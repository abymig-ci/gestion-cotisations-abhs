from .models import Association, Parametre

def parametres_globaux(request):
    association_id = request.session.get('association_id')
    association = None
    parametre = None

    if association_id:
        association = Association.objects.filter(id=association_id).first()
        
    if association:
        parametre = Parametre.objects.filter(association=association).first()
        if not parametre:
            parametre = Parametre.objects.create(
                association=association,
                nom_association=association.nom,
                couleur_principale=association.couleur_principale,
                logo=association.logo
            )

    return {
        'parametre_global': parametre,
        'association_active_id': association_id,
        'association_active': association,
    }