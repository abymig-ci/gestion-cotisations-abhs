from django.urls import path
from . import views

urlpatterns = [
    path('libres/', views.liste_cotisations_libres, name='libres_liste'),
    path('libres/ajouter/', views.editer_cotisation_libre, name='libres_ajouter'),
    path('libres/<int:pk>/', views.detail_cotisation_libre, name='libres_detail'),
    path('libres/<int:pk>/modifier/', views.editer_cotisation_libre, name='libres_modifier'),
    path('libres/<int:pk>/supprimer/', views.supprimer_cotisation_libre, name='libres_supprimer'),
    path('libres/<int:pk>/pdf/', views.cotisation_libre_pdf, name='libres_pdf'),
]
