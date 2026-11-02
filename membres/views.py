from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from decimal import Decimal

from .models import Membre, Groupe, Poste
from .forms import MembreForm, GroupeForm, PosteForm


@login_required
def liste_membres(request):
    groupe_id = request.GET.get('groupe')
    poste_id = request.GET.get('poste')
    
    membres = Membre.objects.annotate(
        nb_cotisations=Count('cotisations'),
        total_paye=Sum('cotisations__montant', filter=Q(cotisations__statut='payee'))
    )
    
    if groupe_id:
        membres = membres.filter(groupe_id=groupe_id)
    if poste_id:
        membres = membres.filter(poste_id=poste_id)
        
    return render(request, 'membres/liste.html', {'membres': membres})


@login_required
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


@login_required
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
    membre = get_object_or_404(Membre, pk=pk)
    cotisations = membre.cotisations.all()
    
    total_agg = cotisations.filter(statut='payee').aggregate(
        total=Coalesce(Sum('montant'), Decimal('0.00'))
    )
    total = total_agg.get('total', 0) or 0

    return render(request, 'membres/detail.html', {
        'membre': membre,
        'cotisations': cotisations,
        'total': total,
    })


@login_required
def liste_groupes(request):
    groupes = Groupe.objects.annotate(nb_membres=Count('membres'))
    return render(request, 'membres/liste_groupes.html', {'groupes': groupes})


@login_required
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

@login_required
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

@login_required
def supprimer_groupe(request, pk):
    groupe = get_object_or_404(Groupe, pk=pk)
    if request.method == 'POST':
        # On détache d'abord tous les membres de ce groupe
        # Cela évite les erreurs de contrainte de clé étrangère
        groupe.membres.update(groupe=None)
        
        # Ensuite, on supprime le groupe
        groupe.delete()
        messages.success(request, "Groupe supprimé. Les membres concernés sont désormais sans groupe.")
        return redirect('liste_groupes')
    return render(request, 'membres/confirmer_suppression_groupe.html', {'groupe': groupe})

@login_required
def liste_postes(request):
    postes = Poste.objects.annotate(nb_membres=Count('membres'))
    return render(request, 'membres/liste_postes.html', {'postes': postes})


@login_required
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

@login_required
def supprimer_membre(request, pk):
    membre = get_object_or_404(Membre, pk=pk)
    if request.method == 'POST':
        membre.delete()
        messages.success(request, "Le membre a été supprimé avec succès.")
        return redirect('liste_membres')
    return render(request, 'membres/confirmer_suppression.html', {'membre': membre})