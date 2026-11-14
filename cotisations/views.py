from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import date
from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, FileResponse
from weasyprint import HTML
from django.template.loader import render_to_string
from django.core.serializers import serialize
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import base64
import os
import json
from datetime import datetime
from django.conf import settings
import requests

from .models import Cotisation, Parametre, Sauvegarde, Association
from .forms import CotisationForm, ParametreForm
from membres.models import Membre, ProfilAcces


# --- HELPERS ---
def get_assoc_id(request):
    return request.session.get('association_id')


# --- FONCTION POUR LE LOGO EN BASE64 ---
def get_logo_base64(request):
    try:
        # On prend le logo de l'association active
        parametre = Parametre.objects.filter(association_id=get_assoc_id(request)).first()
        
        # ⬇️ NOUVEAU : Priorité au logo stocké en texte dans la base de données
        if parametre and parametre.logo_base64:
            return parametre.logo_base64

        # Sinon, on cherche le fichier physique (ancienne méthode)
        if parametre and parametre.logo:
            logo_path = parametre.logo.path
        else:
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
            
        with open(logo_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded_string}"
    except (FileNotFoundError, ValueError):
        return ""


# --- DÉCORATEURS DE SÉCURITÉ ---
def has_acces(user, acces_name):
    if user.is_superuser:
        return True
    try:
        profil = user.profil_acces
        return getattr(profil, acces_name, False)
    except ProfilAcces.DoesNotExist:
        return False

def check_acces(acces_name):
    def decorator(view_func):
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not has_acces(request.user, acces_name):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# --- FORMULAIRE POUR LA COTISATION EXCEPTIONNELLE ---
class CotisationExceptionnelleForm(forms.Form):
    TYPE_COTISATION = [
        ('collective', 'Collective (pour tous les membres)'),
        ('individuelle', 'Individuelle (pour un membre spécifique)'),
    ]
    type_cotisation = forms.ChoiceField(choices=TYPE_COTISATION, widget=forms.Select(attrs={'class': 'form-select'}))
    membre_beneficiaire = forms.ModelChoiceField(
        queryset=Membre.objects.none(),  # Sera rempli dynamiquement
        required=False,
        empty_label="--- Aucun (si collective) ---",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    libelle = forms.CharField(
        max_length=200, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Soutien à un membre, Achat de matériel...'})
    )
    montant = forms.DecimalField(
        max_digits=10, decimal_places=2, 
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )


# --- DASHBOARD ---
@login_required
def dashboard(request):
    today = timezone.now().date()
    annee = today.year
    mois = today.month
    assoc_id = get_assoc_id(request)

    # Paramètres de l'association
    parametre = Parametre.objects.filter(association_id=assoc_id).first()
    if not parametre:
        parametre = Parametre.objects.create(association_id=assoc_id, nom_association="Nouvelle Asso")
    
    montant_standard = parametre.montant_cotisation_mensuelle

    # Membres de l'association
    tous_les_membres = Membre.objects.filter(association_id=assoc_id)
    retards = []
    
    for membre in tous_les_membres:
        statut = membre.statut_cotisation
        if statut == "En retard":
            montant_du = 0
            montant_du_existant = membre.cotisations.filter(statut='en_attente').aggregate(
                total=Sum('montant')
            )['total'] or 0
            montant_du += montant_du_existant
            
            derniere_cot = membre.cotisations.filter(
                type_cotisation='mensuelle', statut='payee'
            ).order_by('-annee', '-mois').first()
            
            if derniere_cot:
                date_debut_calcul = date(derniere_cot.annee, derniere_cot.mois, 1) + relativedelta(months=1)
            else:
                date_debut_calcul = date(membre.date_adhesion.year, membre.date_adhesion.month, 1)
            
            date_fin = date(today.year, today.month, 1)
            
            if date_debut_calcul <= date_fin:
                nb_mois = (date_fin.year - date_debut_calcul.year) * 12 + (date_fin.month - date_debut_calcul.month) + 1
                for i in range(nb_mois):
                    mois_courant = date_debut_calcul + relativedelta(months=i)
                    if not membre.cotisations.filter(type_cotisation='mensuelle', annee=mois_courant.year, mois=mois_courant.month).exists():
                        montant_du += montant_standard

            retards.append({
                'membre': membre,
                'montant_du': montant_du,
                'statut': statut
            })
            
    retards = sorted(retards, key=lambda x: x['montant_du'], reverse=True)

    stats = {
        'total_membres': tous_les_membres.filter(statut='actif').count(),
        'cotisations_mois': parametre.montant_cotisation_mensuelle, 
        'retards': len(retards),
        'total_annee': Cotisation.objects.filter(
            association_id=assoc_id,
            annee=annee, statut='payee'
        ).aggregate(total=Sum('montant'))['total'] or 0,
    }

    derniers_paiements = Cotisation.objects.filter(
        association_id=assoc_id,
        statut='payee'
    ).select_related('membre').order_by('-date_paiement')[:10]

    return render(request, 'cotisations/dashboard.html', {
        'stats': stats,
        'derniers_paiements': derniers_paiements,
        'retards': retards[:10],
        'mois_actuel': mois,
        'annee_actuelle': annee,
    })


# --- COTISATIONS ---

@check_acces('acces_cotisations')
def liste_cotisations(request):
    type_filter = request.GET.get('type', '')
    statut_filter = request.GET.get('statut', '')

    cotisations = Cotisation.objects.filter(association_id=get_assoc_id(request)).select_related('membre').order_by('-date_creation')
    if type_filter:
        cotisations = cotisations.filter(type_cotisation=type_filter)
    if statut_filter:
        cotisations = cotisations.filter(statut=statut_filter)

    return render(request, 'cotisations/liste.html', {
        'cotisations': cotisations,
        'type_filter': type_filter,
        'statut_filter': statut_filter,
        'today': timezone.now().date(),
    })


@check_acces('acces_cotisations')
def ajouter_cotisation(request):
    if request.method == 'POST':
        form = CotisationForm(request.POST)
        if form.is_valid():
            cotisation = form.save(commit=False)
            aujourd_hui = timezone.now().date()
            cotisation.annee = aujourd_hui.year
            cotisation.statut = 'payee'
            cotisation.association_id = get_assoc_id(request)
            
            if cotisation.type_cotisation == 'mensuelle':
                derniere_cotisation = Cotisation.objects.filter(
                    membre=cotisation.membre, 
                    type_cotisation='mensuelle',
                    statut='payee'
                ).order_by('-annee', '-mois').first()

                if derniere_cotisation:
                    date_debut = date(derniere_cotisation.annee, derniere_cotisation.mois, 1) + relativedelta(months=1)
                else:
                    date_debut = date(cotisation.membre.date_adhesion.year, cotisation.membre.date_adhesion.month, 1)
                
                while Cotisation.objects.filter(
                    membre=cotisation.membre, type_cotisation='mensuelle',
                    annee=date_debut.year, mois=date_debut.month, statut='payee'
                ).exists():
                    date_debut = date_debut + relativedelta(months=1)

                cotisation.mois = date_debut.month
                cotisation.annee = date_debut.year
                prochain_mois = date_debut + relativedelta(months=1)
                cotisation.date_echeance = prochain_mois - relativedelta(days=1)
                
                nombre_mois_a_creer = cotisation.nombre_mois if cotisation.nombre_mois else 1
                
                for i in range(nombre_mois_a_creer):
                    date_actuelle = date_debut + relativedelta(months=i)
                    deja_paye = Cotisation.objects.filter(
                        membre=cotisation.membre, type_cotisation='mensuelle',
                        annee=date_actuelle.year, mois=date_actuelle.month
                    ).exists()
                    
                    if not deja_paye:
                        nouvelle_cot = Cotisation(
                            association_id=get_assoc_id(request),
                            membre=cotisation.membre,
                            type_cotisation='mensuelle',
                            montant=cotisation.montant,
                            mois=date_actuelle.month,
                            annee=date_actuelle.year,
                            date_echeance=date_actuelle + relativedelta(day=31),
                            date_paiement=cotisation.date_paiement,
                            statut='payee',
                            observation=cotisation.observation
                        )
                        nouvelle_cot.save()
                
                messages.success(request, f"{nombre_mois_a_creer} mois de cotisations enregistrés à partir de {date_debut.strftime('%B %Y')}.")
                return redirect('liste_cotisations')
                
            else:
                cotisation.mois = None
                cotisation.date_echeance = aujourd_hui
                
            cotisation.save()
            messages.success(request, "Cotisation enregistrée avec succès.")
            return redirect('liste_cotisations')
    else:
        form = CotisationForm()
        form.fields['membre'].queryset = Membre.objects.filter(association_id=get_assoc_id(request))
    
    return render(request, 'cotisations/form.html', {
        'form': form,
        'titre': 'Nouvelle cotisation',
    })


@check_acces('acces_cotisations')
def modifier_cotisation(request, pk):
    cotisation = get_object_or_404(Cotisation, pk=pk)
    if request.method == 'POST':
        form = CotisationForm(request.POST, instance=cotisation)
        if form.is_valid():
            form.save()
            messages.success(request, "Cotisation modifiée avec succès.")
            return redirect('liste_cotisations')
    else:
        form = CotisationForm(instance=cotisation)
        form.fields['membre'].queryset = Membre.objects.filter(association_id=get_assoc_id(request))
    return render(request, 'cotisations/form.html', {
        'form': form,
        'titre': 'Modifier la cotisation',
    })


@check_acces('acces_cotisations')
def marquer_payee(request, pk):
    cotisation = get_object_or_404(Cotisation, pk=pk)
    cotisation.statut = 'payee'
    cotisation.date_paiement = timezone.now().date()
    cotisation.save()
    messages.success(request, "Cotisation marquée comme payée.")
    return redirect('liste_cotisations')


@check_acces('acces_cotisations')
def supprimer_cotisation(request, pk):
    cotisation = get_object_or_404(Cotisation, pk=pk)
    if request.method == 'POST':
        if cotisation.type_cotisation == 'mensuelle':
            derniere_mensuelle = Cotisation.objects.filter(
                membre=cotisation.membre, 
                type_cotisation='mensuelle'
            ).order_by('-annee', '-mois').first()
            if derniere_mensuelle and derniere_mensuelle.pk != cotisation.pk:
                messages.error(request, "Seule la dernière cotisation mensuelle peut être supprimée.")
                return render(request, 'cotisations/confirmer_suppression.html', {'cotisation': cotisation})
        elif cotisation.type_cotisation == 'exceptionnelle':
            derniere_exceptionnelle = Cotisation.objects.filter(
                membre=cotisation.membre, 
                type_cotisation='exceptionnelle'
            ).order_by('-date_creation').first()
            if derniere_exceptionnelle and derniere_exceptionnelle.pk != cotisation.pk:
                messages.error(request, "Seule la dernière cotisation exceptionnelle peut être supprimée.")
                return render(request, 'cotisations/confirmer_suppression.html', {'cotisation': cotisation})

        cotisation.delete()
        messages.success(request, "Cotisation supprimée avec succès.")
        return redirect('liste_cotisations')
        
    return render(request, 'cotisations/confirmer_suppression.html', {
        'cotisation': cotisation,
    })


@check_acces('acces_cotisations')
def creer_cotisation_exceptionnelle(request):
    if request.method == 'POST':
        form = CotisationExceptionnelleForm(request.POST)
        form.fields['membre_beneficiaire'].queryset = Membre.objects.filter(
            association_id=get_assoc_id(request), statut='actif'
        )
        
        if form.is_valid():
            type_cot = form.cleaned_data['type_cotisation']
            beneficiaire = form.cleaned_data['membre_beneficiaire']
            libelle = form.cleaned_data['libelle']
            montant = form.cleaned_data['montant']
            
            date_echeance = timezone.now().date()
            membres_actifs = Membre.objects.filter(
                association_id=get_assoc_id(request), statut='actif'
            )
            
            if type_cot == 'individuelle':
                if not beneficiaire:
                    form.add_error('membre_beneficiaire', "Veuillez choisir un membre bénéficiaire.")
                    return render(request, 'cotisations/form_exceptionnelle.html', {'form': form})
                membres_actifs = membres_actifs.exclude(pk=beneficiaire.pk)
            
            compteur = 0
            for membre in membres_actifs:
                deja_existe = Cotisation.objects.filter(
                    membre=membre, type_cotisation='exceptionnelle', libelle=libelle, montant=montant
                ).exists()
                if not deja_existe:
                    Cotisation.objects.create(
                        association_id=get_assoc_id(request),
                        membre=membre, type_cotisation='exceptionnelle',
                        montant=montant, date_echeance=date_echeance,
                        libelle=libelle, statut='en_attente'
                    )
                    compteur += 1
            
            messages.success(request, f"{compteur} cotisations exceptionnelles créées avec succès.")
            return redirect('liste_cotisations')
    else:
        form = CotisationExceptionnelleForm()
        form.fields['membre_beneficiaire'].queryset = Membre.objects.filter(
            association_id=get_assoc_id(request), statut='actif'
        )
    
    return render(request, 'cotisations/form_exceptionnelle.html', {'form': form})


# --- PARAMETRES ---

@check_acces('acces_parametres')
def parametres(request):
    parametre = Parametre.objects.filter(association_id=get_assoc_id(request)).first()
    if not parametre:
        parametre = Parametre.objects.create(association_id=get_assoc_id(request), nom_association="Nouvelle Asso")
        
    if request.method == 'POST':
        form = ParametreForm(request.POST, request.FILES, instance=parametre)
        if form.is_valid():
            instance = form.save(commit=False)
            
            # ⬇️ CONVERSION EN BASE64 (Pour que le logo persiste sur Render)
            logo_file = request.FILES.get('logo')
            if logo_file:
                # On lit le fichier et on le convertit en texte
                encoded_string = base64.b64encode(logo_file.read()).decode('utf-8')
                mime_type = logo_file.content_type 
                # On sauvegarde la chaîne dans le nouveau champ
                instance.logo_base64 = f"data:{mime_type};base64,{encoded_string}"
            
            instance.save()
            messages.success(request, "Paramètres enregistrés avec succès.")
            return redirect('parametres')
    else:
        form = ParametreForm(instance=parametre)
    return render(request, 'cotisations/parametres.html', {'form': form})


# --- MOTIFS EXCEPTIONNELS ---

@check_acces('acces_cotisations')
def liste_motifs_exceptionnels(request):
    libelles_bruts = Cotisation.objects.filter(
        association_id=get_assoc_id(request),
        type_cotisation='exceptionnelle'
    ).values_list('libelle', flat=True)
    
    libelles_uniques = set()
    for libelle in libelles_bruts:
        if libelle and libelle.strip():
            libelles_uniques.add(libelle.strip())
    
    motifs = []
    for libelle in libelles_uniques:
        cotisations_du_motif = Cotisation.objects.filter(
            association_id=get_assoc_id(request),
            type_cotisation='exceptionnelle', libelle=libelle
        )
        montant_unitaire = cotisations_du_motif.first().montant
        total_collecte = cotisations_du_motif.filter(statut='payee').aggregate(total=Sum('montant'))['total'] or 0
        nb_payes = cotisations_du_motif.filter(statut='payee').count()
        nb_total = cotisations_du_motif.count()
        nb_impayes = nb_total - nb_payes
        
        motifs.append({
            'libelle': libelle,
            'montant_unitaire': montant_unitaire,
            'total_collecte': total_collecte,
            'nb_payes': nb_payes,
            'nb_impayes': nb_impayes,
            'nb_total': nb_total,
        })
    
    motifs = sorted(motifs, key=lambda x: x['libelle'].lower())
    
    return render(request, 'cotisations/liste_motifs_exceptionnels.html', {
        'motifs': motifs,
    })


@check_acces('acces_cotisations')
def detail_motif_exceptionnel(request, libelle):
    cotisations = Cotisation.objects.filter(
        association_id=get_assoc_id(request),
        type_cotisation='exceptionnelle', 
        libelle=libelle
    ).select_related('membre').order_by('membre__nom', 'membre__prenom')
    
    total_collecte = cotisations.filter(statut='payee').aggregate(total=Sum('montant'))['total'] or 0
    nb_payes = cotisations.filter(statut='payee').count()
    nb_impayes = cotisations.filter(statut='en_attente').count()
    
    return render(request, 'cotisations/detail_motif_exceptionnel.html', {
        'libelle': libelle,
        'cotisations': cotisations,
        'total_collecte': total_collecte,
        'nb_payes': nb_payes,
        'nb_impayes': nb_impayes,
    })


@check_acces('acces_cotisations')
def liste_motifs_exceptionnels_pdf(request):
    libelles = Cotisation.objects.filter(
        association_id=get_assoc_id(request),
        type_cotisation='exceptionnelle'
    ).values_list('libelle', flat=True).distinct()
    
    motifs = []
    for libelle in libelles:
        if not libelle:
            continue
            
        cotisations_du_motif = Cotisation.objects.filter(
            association_id=get_assoc_id(request),
            type_cotisation='exceptionnelle', libelle=libelle
        )
        montant_unitaire = cotisations_du_motif.first().montant
        total_collecte = cotisations_du_motif.filter(statut='payee').aggregate(total=Sum('montant'))['total'] or 0
        nb_payes = cotisations_du_motif.filter(statut='payee').count()
        nb_total = cotisations_du_motif.count()
        nb_impayes = nb_total - nb_payes
        
        motifs.append({
            'libelle': libelle,
            'montant_unitaire': montant_unitaire,
            'total_collecte': total_collecte,
            'nb_payes': nb_payes,
            'nb_impayes': nb_impayes,
            'nb_total': nb_total,
        })
    
    motifs = sorted(motifs, key=lambda x: x['libelle'])

    # ⬇️ RÉCUPÉRATION DE L'ASSOCIATION ACTIVE
    assoc_active = Association.objects.filter(id=get_assoc_id(request)).first()

    html_string = render_to_string('cotisations/motifs_exceptionnels_pdf.html', {
        'motifs': motifs,
        'today': timezone.now().date(),
        'logo_base64': get_logo_base64(request),
        'nom_association': assoc_active.nom if assoc_active else "Nom de l'association", # ⬅️ AJOUTÉ
    })

    html = HTML(string=html_string)
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="motifs_exceptionnels.pdf"'
    
    return response


@check_acces('acces_cotisations')
def detail_motif_exceptionnel_pdf(request, libelle):
    cotisations = Cotisation.objects.filter(
        association_id=get_assoc_id(request),
        type_cotisation='exceptionnelle', 
        libelle=libelle
    ).select_related('membre').order_by('membre__nom', 'membre__prenom')
    
    total_collecte = cotisations.filter(statut='payee').aggregate(total=Sum('montant'))['total'] or 0
    nb_payes = cotisations.filter(statut='payee').count()
    nb_impayes = cotisations.filter(statut='en_attente').count()

    # ⬇️ RÉCUPÉRATION DE L'ASSOCIATION ACTIVE
    assoc_active = Association.objects.filter(id=get_assoc_id(request)).first()

    html_string = render_to_string('cotisations/detail_motif_exceptionnel_pdf.html', {
        'libelle': libelle,
        'cotisations': cotisations,
        'total_collecte': total_collecte,
        'nb_payes': nb_payes,
        'nb_impayes': nb_impayes,
        'today': timezone.now().date(),
        'logo_base64': get_logo_base64(request),
        'nom_association': assoc_active.nom if assoc_active else "Nom de l'association", # ⬅️ AJOUTÉ
    })

    html = HTML(string=html_string)
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="detail_{libelle}.pdf"'
    
    return response


# --- SAUVEGARDES ---

@check_acces('acces_sauvegardes')
def liste_sauvegardes(request):
    sauvegardes = Sauvegarde.objects.all()
    return render(request, 'cotisations/sauvegardes.html', {'sauvegardes': sauvegardes})


@check_acces('acces_sauvegardes')
def creer_sauvegarde(request):
    if request.method == 'POST':
        date_str = datetime.now().strftime('%Y-%m-%d-%H%M')
        nom_fichier = f"sauvegarde-{date_str}.json"
        
        from membres.models import Membre, Groupe, Poste, Reunion, ProfilAcces
        from depenses.models import Depense
        
        assoc_id = get_assoc_id(request)
        data = {
            'membres': json.loads(serialize('json', Membre.objects.filter(association_id=assoc_id))),
            'groupes': json.loads(serialize('json', Groupe.objects.filter(association_id=assoc_id))),
            'postes': json.loads(serialize('json', Poste.objects.filter(association_id=assoc_id))),
            'reunions': json.loads(serialize('json', Reunion.objects.filter(association_id=assoc_id))),
            'profils_acces': json.loads(serialize('json', ProfilAcces.objects.all())),
            'cotisations': json.loads(serialize('json', Cotisation.objects.filter(association_id=assoc_id))),
            'parametres': json.loads(serialize('json', Parametre.objects.filter(association_id=assoc_id))),
            'depenses': json.loads(serialize('json', Depense.objects.filter(association_id=assoc_id))),
        }
        
        chemin_fichier = os.path.join('sauvegardes', nom_fichier)
        fichier = default_storage.save(chemin_fichier, ContentFile(json.dumps(data, indent=2).encode('utf-8')))
        
        taille = default_storage.size(fichier)
        Sauvegarde.objects.create(nom_fichier=nom_fichier, taille=taille)
        
        messages.success(request, "Sauvegarde locale créée avec succès.")
        
        sauvegardes = Sauvegarde.objects.all().order_by('-date_creation')
        if sauvegardes.count() > 7:
            for vieille_sauvegarde in sauvegardes[7:]:
                chemin_vieux = os.path.join('sauvegardes', vieille_sauvegarde.nom_fichier)
                if default_storage.exists(chemin_vieux):
                    default_storage.delete(chemin_vieux)
                vieille_sauvegarde.delete()
        
        return redirect('liste_sauvegardes')
    
    return redirect('liste_sauvegardes')


@check_acces('acces_sauvegardes')
def supprimer_sauvegarde(request, pk):
    sauvegarde = get_object_or_404(Sauvegarde, pk=pk)
    if request.method == 'POST':
        chemin = os.path.join('sauvegardes', sauvegarde.nom_fichier)
        if default_storage.exists(chemin):
            default_storage.delete(chemin)
        
        sauvegarde.delete()
        messages.success(request, "Sauvegarde supprimée.")
        return redirect('liste_sauvegardes')
    return render(request, 'cotisations/confirmer_suppression_sauvegarde.html', {'sauvegarde': sauvegarde})


@check_acces('acces_sauvegardes')
def telecharger_sauvegarde(request, pk):
    sauvegarde = get_object_or_404(Sauvegarde, pk=pk)
    chemin = os.path.join('sauvegardes', sauvegarde.nom_fichier)
    
    if default_storage.exists(chemin):
        fichier = default_storage.open(chemin, 'rb')
        response = FileResponse(fichier, as_attachment=True, filename=sauvegarde.nom_fichier)
        return response
    else:
        messages.error(request, "Le fichier physique est introuvable.")
        return redirect('liste_sauvegardes')


# --- GESTION DES ASSOCIATIONS ---

@login_required
def choisir_association(request):
    associations = Association.objects.filter(est_active=True)
    return render(request, 'cotisations/choisir_association.html', {'associations': associations})


@login_required
def selectionner_association(request, pk):
    association = get_object_or_404(Association, pk=pk)
    request.session['association_id'] = association.id
    messages.success(request, f"Vous administrez maintenant : {association.nom}")
    return redirect('dashboard')