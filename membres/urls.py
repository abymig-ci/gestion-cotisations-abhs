from django.urls import path
from . import views


urlpatterns = [
    path('', views.liste_membres, name='liste_membres'),
    path('ajouter/', views.ajouter_membre, name='ajouter_membre'),
    path('<int:pk>/', views.detail_membre, name='detail_membre'),
    path('<int:pk>/modifier/', views.modifier_membre, name='modifier_membre'),
    path('<int:pk>/supprimer/', views.supprimer_membre, name='supprimer_membre'),
    path('groupes/<int:pk>/modifier/', views.modifier_groupe, name='modifier_groupe'),
    path('groupes/<int:pk>/supprimer/', views.supprimer_groupe, name='supprimer_groupe'),
    path('postes/<int:pk>/modifier/', views.modifier_poste, name='modifier_poste'),
    path('reunions/', views.liste_reunions, name='liste_reunions'),
    path('reunions/ajouter/', views.ajouter_reunion, name='ajouter_reunion'),
    path('reunions/<int:pk>/modifier/', views.modifier_reunion, name='modifier_reunion'),
    path('reunions/<int:pk>/supprimer/', views.supprimer_reunion, name='supprimer_reunion'),
    
    # URLs pour les Groupes
    path('groupes/', views.liste_groupes, name='liste_groupes'),
    path('groupes/ajouter/', views.ajouter_groupe, name='ajouter_groupe'),
    
    # URLs pour les Postes
    path('postes/', views.liste_postes, name='liste_postes'),
    path('postes/ajouter/', views.ajouter_poste, name='ajouter_poste'),
]