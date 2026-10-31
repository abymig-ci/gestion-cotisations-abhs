from django.contrib import admin
from .models import Membre


@admin.register(Membre)
class MembreAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'poste', 'telephone', 'statut', 'date_adhesion')
    list_filter = ('statut', 'poste')
    search_fields = ('nom', 'prenom', 'telephone', 'email')