from django.contrib import admin
from .models import Cotisation


@admin.register(Cotisation)
class CotisationAdmin(admin.ModelAdmin):
    list_display = (
        'membre', 'type_cotisation', 'montant',
        'mois', 'annee', 'statut', 'date_echeance', 'date_paiement'
    )
    list_filter = ('type_cotisation', 'statut', 'annee', 'mois')
    search_fields = ('membre__nom', 'membre__prenom', 'libelle')
    date_hierarchy = 'date_echeance'