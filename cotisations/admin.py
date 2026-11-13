from django.contrib import admin
from .models import Cotisation, Parametre, Sauvegarde, Association


@admin.register(Cotisation)
class CotisationAdmin(admin.ModelAdmin):
    list_display = (
        'membre', 'type_cotisation', 'montant',
        'mois', 'annee', 'statut', 'date_echeance', 'date_paiement'
    )
    list_filter = ('type_cotisation', 'statut', 'annee', 'mois')
    search_fields = ('membre__nom', 'membre__prenom', 'libelle')
    date_hierarchy = 'date_echeance'


@admin.register(Parametre)
class ParametreAdmin(admin.ModelAdmin):
    list_display = ('nom_association', 'montant_cotisation_mensuelle')


@admin.register(Sauvegarde)
class SauvegardeAdmin(admin.ModelAdmin):
    list_display = ('nom_fichier', 'date_creation', 'taille')


@admin.register(Association)
class AssociationAdmin(admin.ModelAdmin):
    list_display = ('nom', 'est_active')
    list_filter = ('est_active',)
    search_fields = ('nom',)