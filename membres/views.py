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
from django.urls import reverse
import random
import string

from .models import Membre, Groupe, Poste, Reunion
from .forms import MembreForm, GroupeForm, PosteForm, ReunionForm


# --- DÉCORATEUR DE SÉCURITÉ ---
def admin_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# --- VUES D'ADMINISTRATION (Protégées) ---

@admin_required
def liste_membres(request):
    groupe_id = request.GET.get('groupe')
    poste_id = request.GET.get('poste')
    statut_filter = request.GET.get('statut')
    
    # OPTIMISATION : select_related pour éviter le problème N+1
    membres = Membre.objects.select_related('poste', 'groupe').annotate(
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


@admin_required
def ajouter_membre(request):
    if request.method == 'POST':
        form = MembreForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Membre ajouté avec succès.")
            return redirect('liste_membres')
    else:
        form = MembreForm()
    return render(request, 'membres/form.html', {'form': form, 'titre': 'Nouveau membre'})


@admin_required
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
    # OPTIMISATION : select_related pour charger le poste et le groupe en une fois
    membre = get_object_or_404(Membre.objects.select_related('poste', 'groupe'), pk=pk)
    
    # Sécurité : un membre ne peut voir que son propre profil
    if not request.user.is_superuser:
        if not hasattr(request.user, 'membre_profil') or request.user.membre_profil.pk != membre.pk:
            raise PermissionDenied

    cotisations = membre.cotisations.all()
    
    total_agg = cotisations.filter(statut='payee').aggregate(
        total=Coalesce(Sum('montant'), Decimal('0.00'))
    )
    total = total_agg.get('total', 0) or 0

    return render(request, 'membres/detail.html', {
        'membre': membre,
        'cotisations': cotisations,
        'total': total,
        'today': timezone.now().date(),
    })


@admin_required
def liste_groupes(request):
    groupes = Groupe.objects.annotate(nb_membres=Count('membres'))
    return render(request, 'membres/liste_groupes.html', {'groupes': groupes})


@admin_required
def ajouter_groupe(request):
    if request.method == 'POST':
        form = GroupeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Groupe créé avec succès.")
            return redirect('liste_groupes')
    else:
        form = GroupeForm()
    return render(request, 'membres/form_groupe.html', {'form': form, 'titre': 'Nouveau Groupe'})


@admin_required
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


@admin_required
def supprimer_groupe(request, pk):
    groupe = get_object_or_404(Groupe, pk=pk)
    if request.method == 'POST':
        groupe.membres.update(groupe=None)
        groupe.delete()
        messages.success(request, "Groupe supprimé. Les membres concernés sont désormais sans groupe.")
        return redirect('liste_groupes')
    return render(request, 'membres/confirmer_suppression_groupe.html', {'groupe': groupe})


@admin_required
def liste_postes(request):
    postes = Poste.objects.annotate(nb_membres=Count('membres'))
    return render(request, 'membres/liste_postes.html', {'postes': postes})


@admin_required
def ajouter_poste(request):
    if request.method == 'POST':
        form = PosteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Poste créé avec succès.")
            return redirect('liste_postes')
    else:
        form = PosteForm()
    return render(request, 'membres/form_poste.html', {'form': form, 'titre': 'Nouveau Poste'})


@admin_required
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


@admin_required
def supprimer_membre(request, pk):
    membre = get_object_or_404(Membre, pk=pk)
    if request.method == 'POST':
        membre.delete()
        messages.success(request, "Le membre a été supprimé avec succès.")
        return redirect('liste_membres')
    return render(request, 'membres/confirmer_suppression.html', {'membre': membre})


@admin_required
def liste_reunions(request):
    # OPTIMISATION : select_related pour le groupe
    reunions = Reunion.objects.select_related('groupe').all()
    return render(request, 'membres/liste_reunions.html', {'reunions': reunions})


@admin_required
def ajouter_reunion(request):
    if request.method == 'POST':
        form = ReunionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Réunion programmée avec succès.")
            return redirect('liste_reunions')
    else:
        form = ReunionForm()
    return render(request, 'membres/form_reunion.html', {'form': form, 'titre': 'Programmer une réunion'})


@admin_required
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


@admin_required
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
        # OPTIMISATION : select_related pour le membre
        membre = Membre.objects.select_related('poste', 'groupe').get(pk=request.user.membre_profil.pk)
    except Membre.DoesNotExist:
        return redirect('dashboard')
        
    cotisations = membre.cotisations.all()
    total = cotisations.filter(statut='payee').aggregate(Sum('montant'))['montant__sum'] or 0
    
    return render(request, 'membres/mon_espace.html', {
        'membre': membre,
        'cotisations': cotisations,
        'total': total,
        'today': timezone.now().date()
    })


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


@login_required
def membres_a_jour(request):
    # OPTIMISATION : select_related pour le poste et le groupe
    membres = Membre.objects.filter(statut='actif').select_related('poste', 'groupe').annotate(
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
    # OPTIMISATION : select_related pour le poste et le groupe
    membres = Membre.objects.filter(statut='actif').select_related('poste', 'groupe').annotate(
        nb_cotisations=Count('cotisations'),
        total_paye=Sum('cotisations__montant', filter=Q(cotisations__statut='payee'))
    )
    membres = [m for m in membres if m.statut_cotisation == "En retard"]
    
    return render(request, 'membres/liste_membres_public.html', {
        'membres': membres,
        'titre_page': "Liste des membres en retard",
        'type_liste': 'en_retard'
    })