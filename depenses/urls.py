from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_depenses, name='liste_depenses'),
    path('ajouter/', views.ajouter_depense, name='ajouter_depense'),
    path('<int:pk>/modifier/', views.modifier_depense, name='modifier_depense'),
    path('<int:pk>/supprimer/', views.supprimer_depense, name='supprimer_depense'),
]