from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from decimal import Decimal

from .models import Membre
from .forms import MembreForm


@login_required
def liste_membres(request):
    membres = Membre.objects.annotate(
        nb_cotisations=Count('cotisations'),
        total_paye=Sum(
            'cotisations__montant',
            filter=Q(cotisations__statut='payee')
        ),
    )
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
    return render(request, 'membres/form.html', {
        'form': form,
        'titre': 'Nouveau membre',
    })


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
    return render(request, 'membres/form.html', {
        'form': form,
        'titre': 'Modifier le membre',
    })



@login_required
def detail_membre(request, pk):
    membre = get_object_or_404(Membre, pk=pk)
    cotisations = membre.cotisations.all()
    
    # Calcul sécurisé du total
    total_agg = cotisations.filter(statut='payee').aggregate(
        total=Coalesce(Sum('montant'), Decimal('0.00'))
    )
    total = total_agg.get('total', 0) or 0

    return render(request, 'membres/detail.html', {
        'membre': membre,
        'cotisations': cotisations,
        'total': total,
    })