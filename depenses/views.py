from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import Depense
from .forms import DepenseForm
from cotisations.models import Cotisation

@login_required
def liste_depenses(request):
    depenses = Depense.objects.all()
    total_depenses = depenses.aggregate(total=Sum('montant'))['total'] or 0
    
    # Calcul du solde (Recettes - Dépenses)
    total_cotisations = Cotisation.objects.filter(statut='payee').aggregate(total=Sum('montant'))['total'] or 0
    solde = total_cotisations - total_depenses

    return render(request, 'depenses/liste.html', {
        'depenses': depenses,
        'total_depenses': total_depenses,
        'solde': solde,
    })

@login_required
def ajouter_depense(request):
    if request.method == 'POST':
        form = DepenseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Dépense enregistrée avec succès.")
            return redirect('liste_depenses')
    else:
        form = DepenseForm()
    return render(request, 'depenses/form.html', {'form': form, 'titre': 'Nouvelle Dépense'})

@login_required
def modifier_depense(request, pk):
    depense = get_object_or_404(Depense, pk=pk)
    if request.method == 'POST':
        form = DepenseForm(request.POST, instance=depense)
        if form.is_valid():
            form.save()
            messages.success(request, "Dépense modifiée avec succès.")
            return redirect('liste_depenses')
    else:
        form = DepenseForm(instance=depense)
    return render(request, 'depenses/form.html', {'form': form, 'titre': 'Modifier la Dépense'})

@login_required
def supprimer_depense(request, pk):
    depense = get_object_or_404(Depense, pk=pk)
    if request.method == 'POST':
        depense.delete()
        messages.success(request, "Dépense supprimée.")
        return redirect('liste_depenses')
    return render(request, 'depenses/confirmer_suppression.html', {'depense': depense})