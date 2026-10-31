from django.urls import path
from . import views


urlpatterns = [
    path('', views.liste_membres, name='liste_membres'),
    path('ajouter/', views.ajouter_membre, name='ajouter_membre'),
    path('<int:pk>/', views.detail_membre, name='detail_membre'),
    path('<int:pk>/modifier/', views.modifier_membre, name='modifier_membre'),
]