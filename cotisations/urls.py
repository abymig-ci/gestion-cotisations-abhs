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
    
    # Les URLs avec "pdf/" DOIVENT ÊTRE AVANT celles avec <str:libelle>
    path('motifs-exceptionnels/pdf/', views.liste_motifs_exceptionnels_pdf, name='liste_motifs_exceptionnels_pdf'),
    path('motifs-exceptionnels/<str:libelle>/pdf/', views.detail_motif_exceptionnel_pdf, name='detail_motif_exceptionnel_pdf'),
    
    # URL de détail (doit être en dernier)
    path('motifs-exceptionnels/<str:libelle>/', views.detail_motif_exceptionnel, name='detail_motif_exceptionnel'),
]