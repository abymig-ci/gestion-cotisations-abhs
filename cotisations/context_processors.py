from .models import Parametre

def parametres_globaux(request):
    try:
        parametre = Parametre.objects.first()
    except Parametre.DoesNotExist:
        parametre = None
    return {'parametre_global': parametre}