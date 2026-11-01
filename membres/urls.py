from django.urls import path
from . import views


urlpatterns = [
    path('', views.liste_membres, name='liste_membres'),
    path('ajouter/', views.ajouter_membre, name='ajouter_membre'),
    path('<int:pk>/', views.detail_membre, name='detail_membre'),
    path('<int:pk>/modifier/', views.modifier_membre, name='modifier_membre'),
    
    # URLs pour les Groupes
    path('groupes/', views.liste_groupes, name='liste_groupes'),
    path('groupes/ajouter/', views.ajouter_groupe, name='ajouter_groupe'),
    
    # URLs pour les Postes
    path('postes/', views.liste_postes, name='liste_postes'),
    path('postes/ajouter/', views.ajouter_poste, name='ajouter_poste'),
]