from django.urls import path
from . import empreinte

urlpatterns = [
    path('empreinte/', empreinte.gerer_empreintes, name='empreinte_gerer'),
    path('empreinte/enregistrer/options/', empreinte.options_enregistrement, name='empreinte_options_enreg'),
    path('empreinte/enregistrer/', empreinte.enregistrer_empreinte, name='empreinte_enregistrer'),
    path('empreinte/<int:pk>/supprimer/', empreinte.supprimer_empreinte, name='empreinte_supprimer'),
    path('empreinte/connexion/options/', empreinte.options_connexion, name='empreinte_options_conn'),
    path('empreinte/connexion/', empreinte.connexion_empreinte, name='empreinte_connexion'),
]
