from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.core.exceptions import PermissionDenied
from .models import Depense
from .forms import DepenseForm
from cotisations.models import Cotisation, Parametre
from membres.models import ProfilAcces


# --- HELPERS ---
def get_assoc_id(request):
    return request.session.get('association_id')


def montants_de_depart(request):
    """Montants de départ (dépenses déjà faites, solde en caisse) de l'association active.
    (0, 0) tant que le super utilisateur ne les a pas activés."""
    parametre = Parametre.objects.filter(association_id=get_assoc_id(request)).first()
    if parametre and parametre.montants_initiaux_actifs:
        return parametre.depenses_initiales or 0, parametre.solde_initial or 0
    return 0, 0


# --- DÉCORATEUR POUR LE NOUVEAU SYSTÈME D'ACCÈS ---
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


# --- VUES ADMINISTRATIVES (Trésorier ou Admin) ---

@check_acces('acces_depenses')
def liste_depenses(request):
    # ⬇️ Filtre par association
    depenses = Depense.objects.filter(association_id=get_assoc_id(request))
    depenses_initiales, solde_initial = montants_de_depart(request)
    total_saisi = depenses.aggregate(total=Sum('montant'))['total'] or 0
    total_depenses = total_saisi + depenses_initiales
    
    # ⬇️ Cotisations filtrées par association
    total_cotisations = Cotisation.objects.filter(
        association_id=get_assoc_id(request),
        statut='payee'
    ).aggregate(total=Sum('montant'))['total'] or 0
    # Le solde de départ est déjà net des anciennes dépenses : on y ajoute les mouvements saisis depuis
    solde = solde_initial + total_cotisations - total_saisi

    return render(request, 'depenses/liste.html', {
        'depenses': depenses,
        'total_depenses': total_depenses,
        'solde': solde,
        'depenses_initiales': depenses_initiales,
        'solde_initial': solde_initial,
    })


@check_acces('acces_depenses')
def ajouter_depense(request):
    if request.method == 'POST':
        form = DepenseForm(request.POST)
        if form.is_valid():
            depense = form.save(commit=False)  # ⬇️
            depense.association_id = get_assoc_id(request)
            depense.save()
            messages.success(request, "Dépense enregistrée avec succès.")
            return redirect('liste_depenses')
    else:
        form = DepenseForm()
    return render(request, 'depenses/form.html', {'form': form, 'titre': 'Nouvelle Dépense'})


@check_acces('acces_depenses')
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


@check_acces('acces_depenses')
def supprimer_depense(request, pk):
    depense = get_object_or_404(Depense, pk=pk)
    if request.method == 'POST':
        depense.delete()
        messages.success(request, "Dépense supprimée.")
        return redirect('liste_depenses')
    return render(request, 'depenses/confirmer_suppression.html', {'depense': depense})


# --- VUE PUBLIQUE (Accessible à tous les membres connectés) ---

@login_required
def liste_depenses_publique(request):
    # ⬇️ Filtre par association
    depenses = Depense.objects.filter(association_id=get_assoc_id(request))
    depenses_initiales, solde_initial = montants_de_depart(request)
    total_saisi = depenses.aggregate(total=Sum('montant'))['total'] or 0
    total_depenses = total_saisi + depenses_initiales
    
    # ⬇️ Cotisations filtrées par association
    total_cotisations = Cotisation.objects.filter(
        association_id=get_assoc_id(request),
        statut='payee'
    ).aggregate(total=Sum('montant'))['total'] or 0
    # Le solde de départ est déjà net des anciennes dépenses : on y ajoute les mouvements saisis depuis
    solde = solde_initial + total_cotisations - total_saisi
    
    return render(request, 'depenses/liste_publique.html', {
        'depenses': depenses,
        'total_depenses': total_depenses,
        'total_cotisations': total_cotisations,
        'solde': solde,
        'depenses_initiales': depenses_initiales,
        'solde_initial': solde_initial,
    })