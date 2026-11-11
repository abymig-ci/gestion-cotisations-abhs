from django.urls import path
from . import views


urlpatterns = [
    path('', views.liste_membres, name='liste_membres'),
    path('ajouter/', views.ajouter_membre, name='ajouter_membre'),
    path('<int:pk>/', views.detail_membre, name='detail_membre'),
    path('<int:pk>/modifier/', views.modifier_membre, name='modifier_membre'),
    path('<int:pk>/supprimer/', views.supprimer_membre, name='supprimer_membre'),
    path('acces/', views.gerer_acces_utilisateurs, name='gerer_acces_utilisateurs'),
    path('acces/<int:user_id>/', views.modifier_acces_utilisateur, name='modifier_acces_utilisateur'),
    
    # URL pour le lien d'invitation (doit être AVANT les autres pour éviter les conflits)
    path('invitation/<str:token>/', views.definir_mot_de_passe, name='definir_mot_de_passe'),
    
    path('groupes/', views.liste_groupes, name='liste_groupes'),
    path('groupes/ajouter/', views.ajouter_groupe, name='ajouter_groupe'),
    path('groupes/<int:pk>/modifier/', views.modifier_groupe, name='modifier_groupe'),
    path('groupes/<int:pk>/supprimer/', views.supprimer_groupe, name='supprimer_groupe'),
    
    path('postes/', views.liste_postes, name='liste_postes'),
    path('postes/ajouter/', views.ajouter_poste, name='ajouter_poste'),
    path('postes/<int:pk>/modifier/', views.modifier_poste, name='modifier_poste'),
    
    path('reunions/', views.liste_reunions, name='liste_reunions'),
    path('reunions/ajouter/', views.ajouter_reunion, name='ajouter_reunion'),
    path('reunions/<int:pk>/modifier/', views.modifier_reunion, name='modifier_reunion'),
    path('reunions/<int:pk>/supprimer/', views.supprimer_reunion, name='supprimer_reunion'),
    
    path('mon-espace/', views.mon_espace, name='mon_espace'),
    path('<int:pk>/creer-acces/', views.creer_acces_membre, name='creer_acces_membre'),
    path('<int:pk>/reinitialiser/', views.reinitialiser_mot_de_passe, name='reinitialiser_mot_de_passe'),
    path('public/a-jour/', views.membres_a_jour, name='membres_a_jour'),
    path('public/en-retard/', views.membres_en_retard, name='membres_en_retard'),
    
    # NOUVELLE URL POUR LE PDF
    path('etat-cotisations-pdf/', views.etat_cotisations_pdf, name='etat_cotisations_pdf'),
]