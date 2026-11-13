from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cotisations/', views.liste_cotisations, name='liste_cotisations'),
    path('cotisations/ajouter/', views.ajouter_cotisation, name='ajouter_cotisation'),
    path('cotisations/<int:pk>/modifier/', views.modifier_cotisation, name='modifier_cotisation'),
    path('cotisations/<int:pk>/payee/', views.marquer_payee, name='marquer_payee'),
    path('cotisations/<int:pk>/supprimer/', views.supprimer_cotisation, name='supprimer_cotisation'),
    path('cotisations/exceptionnelle/ajouter/', views.creer_cotisation_exceptionnelle, name='creer_cotisation_exceptionnelle'),
    path('parametres/', views.parametres, name='parametres'),
    
    # URLs pour les motifs exceptionnels
    path('motifs-exceptionnels/', views.liste_motifs_exceptionnels, name='liste_motifs_exceptionnels'),
    path('motifs-exceptionnels/pdf/', views.liste_motifs_exceptionnels_pdf, name='liste_motifs_exceptionnels_pdf'),
    path('motifs-exceptionnels/<str:libelle>/pdf/', views.detail_motif_exceptionnel_pdf, name='detail_motif_exceptionnel_pdf'),
    path('motifs-exceptionnels/<str:libelle>/', views.detail_motif_exceptionnel, name='detail_motif_exceptionnel'),
    
    # URLs pour les sauvegardes
    path('sauvegardes/', views.liste_sauvegardes, name='liste_sauvegardes'),
    path('sauvegardes/creer/', views.creer_sauvegarde, name='creer_sauvegarde'),
    path('sauvegardes/<int:pk>/supprimer/', views.supprimer_sauvegarde, name='supprimer_sauvegarde'),
    # AJOUT DE L'URL DE TÉLÉCHARGEMENT
    path('sauvegardes/<int:pk>/telecharger/', views.telecharger_sauvegarde, name='telecharger_sauvegarde'),
    path('choisir-association/', views.choisir_association, name='choisir_association'),
    path('choisir-association/', views.choisir_association, name='choisir_association'),
    path('choisir-association/<int:pk>/selectionner/', views.selectionner_association, name='selectionner_association'),
]