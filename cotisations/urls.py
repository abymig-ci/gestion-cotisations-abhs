from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cotisations/', views.liste_cotisations, name='liste_cotisations'),
    path('cotisations/ajouter/', views.ajouter_cotisation, name='ajouter_cotisation'),
    path('cotisations/<int:pk>/modifier/', views.modifier_cotisation, name='modifier_cotisation'),
    path('cotisations/<int:pk>/payee/', views.marquer_payee, name='marquer_payee'),
    path('cotisations/<int:pk>/supprimer/', views.supprimer_cotisation, name='supprimer_cotisation'),
]