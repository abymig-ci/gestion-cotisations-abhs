from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone

from .models import Cotisation
from .forms import CotisationForm
from membres.models import Membre


@login_required
def dashboard(request):
    today = timezone.now().date()
    annee = today.year
    mois = today.month

    stats = {
        'total_membres': Membre.objects.filter(statut='actif').count(),
        'cotisations_mois': Cotisation.objects.filter(
            type_cotisation='mensuelle', mois=mois, annee=annee, statut='payee'
        ).aggregate(total=Sum('montant'))['total'] or 0,
        'retards': Cotisation.objects.filter(statut='retard').count(),
        'total_annee': Cotisation.objects.filter(
            annee=annee, statut='payee'
        ).aggregate(total=Sum('montant'))['total'] or 0,
    }

    derniers_paiements = Cotisation.objects.filter(
        statut='payee'
    ).select_related('membre').order_by('-date_paiement')[:10]

    retards = Cotisation.objects.filter(
        statut='retard'
    ).select_related('membre')[:10]

    return render(request, 'cotisations/dashboard.html', {
        'stats': stats,
        'derniers_paiements': derniers_paiements,
        'retards': retards,
        'mois_actuel': mois,
        'annee_actuelle': annee,
    })


@login_required
def liste_cotisations(request):
    type_filter = request.GET.get('type', '')
    statut_filter = request.GET.get('statut', '')

    cotisations = Cotisation.objects.select_related('membre')
    if type_filter:
        cotisations = cotisations.filter(type_cotisation=type_filter)
    if statut_filter:
        cotisations = cotisations.filter(statut=statut_filter)

    return render(request, 'cotisations/liste.html', {
        'cotisations': cotisations,
        'type_filter': type_filter,
        'statut_filter': statut_filter,
    })


@login_required
def ajouter_cotisation(request):
    if request.method == 'POST':
        form = CotisationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cotisation enregistrée avec succès.")
            return redirect('liste_cotisations')
    else:
        form = CotisationForm()
    return render(request, 'cotisations/form.html', {
        'form': form,
        'titre': 'Nouvelle cotisation',
    })


@login_required
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
    return render(request, 'cotisations/form.html', {
        'form': form,
        'titre': 'Modifier la cotisation',
    })


@login_required
def marquer_payee(request, pk):
    cotisation = get_object_or_404(Cotisation, pk=pk)
    cotisation.statut = 'payee'
    cotisation.date_paiement = timezone.now().date()
    cotisation.save()
    messages.success(request, "Cotisation marquée comme payée.")
    return redirect('liste_cotisations')


@login_required
def supprimer_cotisation(request, pk):
    cotisation = get_object_or_404(Cotisation, pk=pk)
    if request.method == 'POST':
        cotisation.delete()
        messages.success(request, "Cotisation supprimée.")
        return redirect('liste_cotisations')
    return render(request, 'cotisations/confirmer_suppression.html', {
        'cotisation': cotisation,
    })