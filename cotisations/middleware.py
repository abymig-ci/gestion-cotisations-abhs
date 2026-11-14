from membres.models import Membre


class AssociationDuMembreMiddleware:
    """Pour un utilisateur qui n'est pas super utilisateur, l'association active est toujours
    celle de sa fiche membre (Membre.utilisateur). Il ne peut donc pas en choisir une autre.
    Le super utilisateur, lui, choisit son association sur la page « Choisir une association ».
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and not user.is_superuser:
            # La fiche membre n'est relue qu'une fois par session et par utilisateur
            if request.session.get('association_fixee_pour') != user.id:
                membre = Membre.objects.filter(utilisateur=user).only('association_id').first()
                if membre and membre.association_id:
                    request.session['association_id'] = membre.association_id
                    request.session['association_fixee_pour'] = user.id
        return self.get_response(request)
