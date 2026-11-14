from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.http import HttpResponse
from weasyprint import HTML
from django.template.loader import render_to_string
import base64
import os
from django.conf import settings
from datetime import date
from dateutil.relativedelta import relativedelta

from .models import Membre, Groupe, Poste, Reunion, ProfilAcces
from .forms import MembreForm, GroupeForm, PosteForm, ReunionForm


# --- HELPERS ---
def get_assoc_id(request):
    return request.session.get('association_id')


# --- FONCTION POUR LE LOGO EN BASE64 ---
def get_logo_base64(request):
    try:
        from cotisations.models import Parametre
        # On prend le logo de l'association active
        parametre = Parametre.objects.filter(association_id=get_assoc_id(request)).first()
        
        # ⬇️ NOUVEAU : Priorité au logo stocké en texte (Base64) dans la base de données
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
def admin_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view


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


# --- VUES D'ADMINISTRATION DES MEMBRES ---

@check_acces('acces_membres')
def liste_membres(request):
    groupe_id = request.GET.get('groupe')
    poste_id = request.GET.get('poste')
    statut_filter = request.GET.get('statut')
    
    # ⬇️ FILTRE PAR ASSOCIATION ⬇️
    membres = Membre.objects.filter(association_id=get_assoc_id(request)).select_related('poste', 'groupe').annotate(
        nb_cotisations=Count('cotisations'),
        total_paye=Sum('cotisations__montant', filter=Q(cotisations__statut='payee'))
    )
    
    if groupe_id:
        membres = membres.filter(groupe_id=groupe_id)
    if poste_id:
        membres = membres.filter(poste_id=poste_id)
    
    if statut_filter == 'non_a_jour':
        membres = [m for m in membres if m.statut_cotisation == "En retard"]
    elif statut_filter == 'a_jour':
        membres = [m for m in membres if m.statut_cotisation != "En retard"]
        
    return render(request, 'membres/liste.html', {
        'membres': membres,
        'statut_filter': statut_filter,
    })


@check_acces('acces_membres')
def ajouter_membre(request):
    if request.method == 'POST':
        form = MembreForm(request.POST)
        if form.is_valid():
            membre = form.save(commit=False)  # ⬇️ On ne sauvegarde pas tout de suite
            membre.association_id = get_assoc_id(request)  # ⬇️ On assigne l'association
            membre.save()
            messages.success(request, "Membre ajouté avec succès.")
            return redirect('liste_membres')
    else:
        form = MembreForm()
    return render(request, 'membres/form.html', {'form': form, 'titre': 'Nouveau membre'})


@check_acces('acces_membres')
def modifier_membre(request, pk):
    membre = get_object_or_404(Membre, pk=pk)
    if request.method == 'POST':
        form = MembreForm(request.POST, instance=membre)
        if form.is_valid():
            form.save()
            messages.success(request, "Membre modifié avec succès.")
            return redirect('liste_membres')
    else:
        form = MembreForm(instance=membre)
    return render(request, 'membres/form.html', {'form': form, 'titre': 'Modifier le membre'})


@login_required
def detail_membre(request, pk):
    membre = get_object_or_404(Membre.objects.select_related('poste', 'groupe'), pk=pk)
    
    if not request.user.is_superuser:
        if not hasattr(request.user, 'membre_profil') or request.user.membre_profil.pk != membre.pk:
            raise PermissionDenied

    cotisations = membre.cotisations.all()
    
    total_agg = cotisations.filter(statut='payee').aggregate(
        total=Coalesce(Sum('montant'), Decimal('0.00'))
    )
    total = total_agg.get('total', 0) or 0

    # --- CALCUL DES MONTANTS DÛS ---
    montant_du = 0
    montant_assiste = 0
    from cotisations.models import Parametre
    
    # ⬇️ Paramètres de l'association active
    parametre = Parametre.objects.filter(association_id=get_assoc_id(request)).first()
    montant_standard = parametre.montant_cotisation_mensuelle if parametre else 5000
    base_calcul = parametre.base_calcul_date if parametre else 'derniere_reunion'
    mois_tolerance = parametre.nombre_mois_tolerance if parametre else 4
    
    # 1. Cotisations en attente
    montant_du += cotisations.filter(statut='en_attente').aggregate(
        total=Sum('montant')
    )['total'] or 0
    
    # 2. Mois de retard non enregistrés
    if membre.statut == 'actif' and membre.statut_cotisation != "En carence":
        if base_calcul == 'derniere_reunion':
            # ⬇️ Réunions de l'association active
            derniere_reunion = Reunion.objects.filter(
                association_id=get_assoc_id(request),
                date_reunion__lte=timezone.now()
            ).order_by('-date_reunion').first()
            if derniere_reunion:
                date_reference = derniere_reunion.date_reunion.date()
            else:
                date_reference = timezone.now().date()
        else:
            date_reference = timezone.now().date()
            
        date_limite = date_reference - relativedelta(months=mois_tolerance)
        
        derniere_cot = cotisations.filter(
            type_cotisation='mensuelle', statut='payee'
        ).order_by('-annee', '-mois').first()
        
        if derniere_cot:
            date_debut = date(derniere_cot.annee, derniere_cot.mois, 1) + relativedelta(months=1)
        else:
            date_debut = date(membre.date_adhesion.year, membre.date_adhesion.month, 1)
        
        today = timezone.now().date()
        date_fin = date(today.year, today.month, 1)
        
        if date_debut <= date_fin:
            nb_mois = (date_fin.year - date_debut.year) * 12 + (date_fin.month - date_debut.month) + 1
            for i in range(nb_mois):
                mois_courant = date_debut + relativedelta(months=i)
                if not cotisations.filter(type_cotisation='mensuelle', annee=mois_courant.year, mois=mois_courant.month).exists():
                    montant_du += montant_standard
                    if mois_courant <= date_limite:
                        montant_assiste += montant_standard
    # -----------------------------

    return render(request, 'membres/detail.html', {
        'membre': membre,
        'cotisations': cotisations,
        'total': total,
        'montant_du': montant_du,
        'montant_assiste': montant_assiste,
        'today': timezone.now().date(),
    })


@check_acces('acces_membres')
def supprimer_membre(request, pk):
    membre = get_object_or_404(Membre, pk=pk)
    if request.method == 'POST':
        membre.delete()
        messages.success(request, "Le membre a été supprimé avec succès.")
        return redirect('liste_membres')
    return render(request, 'membres/confirmer_suppression.html', {'membre': membre})


# --- VUES DES GROUPES ---

@check_acces('acces_groupes')
def liste_groupes(request):
    # ⬇️ Filtre par association
    groupes = Groupe.objects.filter(association_id=get_assoc_id(request)).annotate(nb_membres=Count('membres'))
    return render(request, 'membres/liste_groupes.html', {'groupes': groupes})


@check_acces('acces_groupes')
def ajouter_groupe(request):
    if request.method == 'POST':
        form = GroupeForm(request.POST)
        if form.is_valid():
            groupe = form.save(commit=False)
            groupe.association_id = get_assoc_id(request)  # ⬇️ Assignation
            groupe.save()
            messages.success(request, "Groupe créé avec succès.")
            return redirect('liste_groupes')
    else:
        form = GroupeForm()
    return render(request, 'membres/form_groupe.html', {'form': form, 'titre': 'Nouveau Groupe'})


@check_acces('acces_groupes')
def modifier_groupe(request, pk):
    groupe = get_object_or_404(Groupe, pk=pk)
    if request.method == 'POST':
        form = GroupeForm(request.POST, instance=groupe)
        if form.is_valid():
            form.save()
            messages.success(request, "Groupe modifié avec succès.")
            return redirect('liste_groupes')
    else:
        form = GroupeForm(instance=groupe)
    return render(request, 'membres/form_groupe.html', {'form': form, 'titre': 'Modifier le Groupe'})


@check_acces('acces_groupes')
def supprimer_groupe(request, pk):
    groupe = get_object_or_404(Groupe, pk=pk)
    if request.method == 'POST':
        groupe.membres.update(groupe=None)
        groupe.delete()
        messages.success(request, "Groupe supprimé. Les membres concernés sont désormais sans groupe.")
        return redirect('liste_groupes')
    return render(request, 'membres/confirmer_suppression_groupe.html', {'groupe': groupe})


# --- VUES DES POSTES ---

@check_acces('acces_postes')
def liste_postes(request):
    # ⬇️ Filtre par association
    postes = Poste.objects.filter(association_id=get_assoc_id(request)).annotate(nb_membres=Count('membres'))
    return render(request, 'membres/liste_postes.html', {'postes': postes})


@check_acces('acces_postes')
def ajouter_poste(request):
    if request.method == 'POST':
        form = PosteForm(request.POST)
        if form.is_valid():
            poste = form.save(commit=False)
            poste.association_id = get_assoc_id(request)  # ⬇️ Assignation
            poste.save()
            messages.success(request, "Poste créé avec succès.")
            return redirect('liste_postes')
    else:
        form = PosteForm()
    return render(request, 'membres/form_poste.html', {'form': form, 'titre': 'Nouveau Poste'})


@check_acces('acces_postes')
def modifier_poste(request, pk):
    poste = get_object_or_404(Poste, pk=pk)
    if request.method == 'POST':
        form = PosteForm(request.POST, instance=poste)
        if form.is_valid():
            form.save()
            messages.success(request, "Poste modifié avec succès.")
            return redirect('liste_postes')
    else:
        form = PosteForm(instance=poste)
    return render(request, 'membres/form_poste.html', {'form': form, 'titre': 'Modifier le Poste'})


# --- VUES DES RÉUNIONS ---

@check_acces('acces_reunions')
def liste_reunions(request):
    # ⬇️ Filtre par association
    reunions = Reunion.objects.filter(association_id=get_assoc_id(request)).select_related('groupe').all()
    return render(request, 'membres/liste_reunions.html', {'reunions': reunions})


@check_acces('acces_reunions')
def ajouter_reunion(request):
    if request.method == 'POST':
        form = ReunionForm(request.POST)
        if form.is_valid():
            reunion = form.save(commit=False)
            reunion.association_id = get_assoc_id(request)  # ⬇️ Assignation
            reunion.save()
            messages.success(request, "Réunion programmée avec succès.")
            return redirect('liste_reunions')
    else:
        form = ReunionForm()
    return render(request, 'membres/form_reunion.html', {'form': form, 'titre': 'Programmer une réunion'})


@check_acces('acces_reunions')
def modifier_reunion(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    if request.method == 'POST':
        form = ReunionForm(request.POST, instance=reunion)
        if form.is_valid():
            form.save()
            messages.success(request, "Réunion modifiée avec succès.")
            return redirect('liste_reunions')
    else:
        form = ReunionForm(instance=reunion)
    return render(request, 'membres/form_reunion.html', {'form': form, 'titre': 'Modifier la réunion'})


@check_acces('acces_reunions')
def supprimer_reunion(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    if request.method == 'POST':
        reunion.delete()
        messages.success(request, "Réunion supprimée.")
        return redirect('liste_reunions')
    return render(request, 'membres/confirmer_suppression_reunion.html', {'reunion': reunion})


# --- VUES ACCESSIBLES AUX MEMBRES ---

@login_required
def mon_espace(request):
    try:
        membre = Membre.objects.select_related('poste', 'groupe').get(pk=request.user.membre_profil.pk)
    except Membre.DoesNotExist:
        return redirect('dashboard')
        
    cotisations = membre.cotisations.all()
    total = cotisations.filter(statut='payee').aggregate(Sum('montant'))['montant__sum'] or 0
    
    # --- CALCUL DES MONTANTS DÛS ---
    montant_du = 0
    montant_assiste = 0
    
    from cotisations.models import Parametre
    
    # ⬇️ Paramètres de l'association active
    parametre = Parametre.objects.filter(association_id=get_assoc_id(request)).first()
    montant_standard = parametre.montant_cotisation_mensuelle if parametre else 5000
    base_calcul = parametre.base_calcul_date if parametre else 'derniere_reunion'
    mois_tolerance = parametre.nombre_mois_tolerance if parametre else 4
    
    # 1. Cotisations en attente
    montant_en_attente = cotisations.filter(statut='en_attente').aggregate(
        total=Sum('montant')
    )['total'] or 0
    montant_du += montant_en_attente
    montant_assiste += montant_en_attente
    
    # 2. Mois de retard non enregistrés
    if membre.statut == 'actif' and membre.statut_cotisation != "En carence":
        if base_calcul == 'derniere_reunion':
            # ⬇️ Réunions de l'association active
            derniere_reunion = Reunion.objects.filter(
                association_id=get_assoc_id(request),
                date_reunion__lte=timezone.now()
            ).order_by('-date_reunion').first()
            if derniere_reunion:
                date_reference = derniere_reunion.date_reunion.date()
            else:
                date_reference = timezone.now().date()
        else:
            date_reference = timezone.now().date()
            
        date_limite = date_reference - relativedelta(months=mois_tolerance)
        
        derniere_cot = cotisations.filter(
            type_cotisation='mensuelle', statut='payee'
        ).order_by('-annee', '-mois').first()
        
        if derniere_cot:
            date_debut = date(derniere_cot.annee, derniere_cot.mois, 1) + relativedelta(months=1)
        else:
            date_debut = date(membre.date_adhesion.year, membre.date_adhesion.month, 1)
        
        today = timezone.now().date()
        date_fin = date(today.year, today.month, 1)
        
        if date_debut <= date_fin:
            nb_mois = (date_fin.year - date_debut.year) * 12 + (date_fin.month - date_debut.month) + 1
            for i in range(nb_mois):
                mois_courant = date_debut + relativedelta(months=i)
                if not cotisations.filter(type_cotisation='mensuelle', annee=mois_courant.year, mois=mois_courant.month).exists():
                    montant_du += montant_standard
                    if mois_courant <= date_limite:
                        montant_assiste += montant_standard

    return render(request, 'membres/mon_espace.html', {
        'membre': membre,
        'cotisations': cotisations,
        'total': total,
        'montant_du': montant_du,
        'montant_assiste': montant_assiste,
        'today': timezone.now().date()
    })


@login_required
def membres_a_jour(request):
    # ⬇️ Filtre par association
    membres = Membre.objects.filter(
        association_id=get_assoc_id(request), 
        statut='actif'
    ).select_related('poste', 'groupe').annotate(
        nb_cotisations=Count('cotisations'),
        total_paye=Sum('cotisations__montant', filter=Q(cotisations__statut='payee'))
    )
    membres = [m for m in membres if m.statut_cotisation != "En retard"]
    
    return render(request, 'membres/liste_membres_public.html', {
        'membres': membres,
        'titre_page': "Liste des membres à jour",
        'type_liste': 'a_jour'
    })


@login_required
def membres_en_retard(request):
    # ⬇️ Filtre par association
    membres = Membre.objects.filter(
        association_id=get_assoc_id(request), 
        statut='actif'
    ).select_related('poste', 'groupe').annotate(
        nb_cotisations=Count('cotisations'),
        total_paye=Sum('cotisations__montant', filter=Q(cotisations__statut='payee'))
    )
    membres = [m for m in membres if m.statut_cotisation == "En retard"]
    
    return render(request, 'membres/liste_membres_public.html', {
        'membres': membres,
        'titre_page': "Liste des membres en retard",
        'type_liste': 'en_retard'
    })


# --- GESTION DES ACCÈS UTILISATEURS ---

@admin_required
def gerer_acces_utilisateurs(request):
    utilisateurs = User.objects.filter(is_superuser=False)
    return render(request, 'membres/gerer_acces.html', {'utilisateurs': utilisateurs})


@admin_required
def modifier_acces_utilisateur(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    profil, created = ProfilAcces.objects.get_or_create(utilisateur=user)
    
    if request.method == 'POST':
        profil.acces_membres = request.POST.get('acces_membres') == 'on'
        profil.acces_cotisations = request.POST.get('acces_cotisations') == 'on'
        profil.acces_depenses = request.POST.get('acces_depenses') == 'on'
        profil.acces_reunions = request.POST.get('acces_reunions') == 'on'
        profil.acces_groupes = request.POST.get('acces_groupes') == 'on'
        profil.acces_postes = request.POST.get('acces_postes') == 'on'
        profil.acces_parametres = request.POST.get('acces_parametres') == 'on'
        profil.acces_sauvegardes = request.POST.get('acces_sauvegardes') == 'on'
        profil.save()
        
        messages.success(request, f"Accès de {user.username} mis à jour.")
        return redirect('gerer_acces_utilisateurs')
        
    return render(request, 'membres/modifier_acces.html', {
        'user_obj': user,
        'profil': profil
    })


# --- CRÉATION D'ACCÈS (INVITATION) ---

@admin_required
def creer_acces_membre(request, pk):
    membre = get_object_or_404(Membre, pk=pk)
    
    if membre.utilisateur:
        messages.warning(request, "Ce membre a déjà un accès.")
        return redirect('detail_membre', pk=membre.pk)
        
    if request.method == 'POST':
        username = request.POST.get('username')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà pris.")
        else:
            token = get_random_string(length=32)
            
            user = User.objects.create_user(username=username, password=get_random_string(length=32))
            user.is_active = False
            user.save()
            
            membre.utilisateur = user
            membre.invitation_token = token
            membre.invitation_date = timezone.now()
            membre.save()
            
            messages.success(request, f"Lien d'invitation généré pour {username}. Copiez-le et envoyez-le au membre.")
            return redirect('detail_membre', pk=membre.pk)

    return render(request, 'membres/creer_acces.html', {'membre': membre})


@admin_required
def reinitialiser_mot_de_passe(request, pk):
    membre = get_object_or_404(Membre, pk=pk)
    
    if not membre.utilisateur:
        messages.warning(request, "Ce membre n'a pas encore de compte. Utilisez 'Créer un accès' d'abord.")
        return redirect('detail_membre', pk=membre.pk)

    if request.method == 'POST':
        token = get_random_string(length=32)
        membre.invitation_token = token
        membre.invitation_date = timezone.now()
        membre.save()
        
        messages.success(request, f"Lien de réinitialisation généré pour {membre.utilisateur.username}. Copiez-le et envoyez-le au membre.")
        return redirect('detail_membre', pk=membre.pk)

    return render(request, 'membres/reinitialiser_acces.html', {'membre': membre})


# --- VUE PUBLIQUE POUR DÉFINIR LE MOT DE PASSE ---

def definir_mot_de_passe(request, token):
    try:
        membre = Membre.objects.get(invitation_token=token)
    except Membre.DoesNotExist:
        messages.error(request, "Lien invalide ou expiré.")
        return redirect('login')
        
    if membre.invitation_date and (timezone.now() - membre.invitation_date).days > 7:
        messages.error(request, "Ce lien a expiré. Contactez l'administrateur.")
        return redirect('login')

    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        if password != password_confirm:
            messages.error(request, "Les mots de passe ne correspondent pas.")
        elif len(password) < 8:
            messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
        else:
            user = membre.utilisateur
            user.set_password(password)
            user.is_active = True
            user.save()
            
            membre.invitation_token = None
            membre.invitation_date = None
            membre.save()
            
            messages.success(request, "Votre mot de passe a été créé. Vous pouvez maintenant vous connecter.")
            return redirect('login')

    return render(request, 'membres/definir_mot_de_passe.html', {'token': token})


@admin_required
def etat_cotisations_pdf(request):
    # ⬇️ Filtre par association
    groupes = Groupe.objects.filter(association_id=get_assoc_id(request)).order_by('nom')
    etat_par_groupe = []
    
    for groupe in groupes:
        membres_du_groupe = Membre.objects.filter(
            association_id=get_assoc_id(request),
            statut='actif', groupe=groupe
        ).select_related('poste').order_by('nom', 'prenom')
        
        liste_membres = []
        for membre in membres_du_groupe:
            derniere_mensuelle = membre.cotisations.filter(
                type_cotisation='mensuelle', statut='payee'
            ).order_by('-annee', '-mois').first()
            
            total_paye = membre.cotisations.filter(statut='payee').aggregate(
                total=Sum('montant')
            )['total'] or 0
            
            exceptionnelles_impayees = membre.cotisations.filter(
                type_cotisation='exceptionnelle', statut='en_attente'
            )
            
            liste_membres.append({
                'membre': membre,
                'derniere_mensuelle': derniere_mensuelle,
                'total_paye': total_paye,
                'exceptionnelles_impayees': exceptionnelles_impayees,
            })
        
        if liste_membres:
            etat_par_groupe.append({
                'groupe': groupe,
                'membres': liste_membres,
                'total_groupe': sum(m['total_paye'] for m in liste_membres)
            })
    
    membres_sans_groupe = Membre.objects.filter(
        association_id=get_assoc_id(request),
        statut='actif', groupe__isnull=True
    ).select_related('poste').order_by('nom', 'prenom')
    
    if membres_sans_groupe.exists():
        liste_sans_groupe = []
        for membre in membres_sans_groupe:
            derniere_mensuelle = membre.cotisations.filter(type_cotisation='mensuelle', statut='payee').order_by('-annee', '-mois').first()
            total_paye = membre.cotisations.filter(statut='payee').aggregate(total=Sum('montant'))['total'] or 0
            exceptionnelles_impayees = membre.cotisations.filter(type_cotisation='exceptionnelle', statut='en_attente')
            liste_sans_groupe.append({
                'membre': membre,
                'derniere_mensuelle': derniere_mensuelle,
                'total_paye': total_paye,
                'exceptionnelles_impayees': exceptionnelles_impayees,
            })
        etat_par_groupe.append({
            'groupe': None,
            'membres': liste_sans_groupe,
            'total_groupe': sum(m['total_paye'] for m in liste_sans_groupe)
        })

    # ⬇️ NOUVEAU : On récupère l'association active pour le PDF
    from cotisations.models import Association
    assoc_active = Association.objects.filter(id=get_assoc_id(request)).first()

    html_string = render_to_string('membres/etat_cotisations_pdf.html', {
        'etat_par_groupe': etat_par_groupe,
        'today': timezone.now().date(),
        'logo_base64': get_logo_base64(request), # ⬅️ On passe request
        'nom_association': assoc_active.nom if assoc_active else "Nom de l'association", # ⬅️ NOUVEAU
    })

    html = HTML(string=html_string)
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="etat_cotisations.pdf"'
    
    return response