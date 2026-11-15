from django.shortcuts import redirect

from membres.models import Membre

from .models import Association

# Adresses accessibles au super utilisateur même sans association choisie
# ('/pwa/' : fichiers d'installation de l'application sur l'écran d'accueil)
ADRESSES_LIBRES = ('/login/', '/logout/', '/choisir-association/', '/admin/', '/static/', '/media/', '/favicon.ico', '/pwa/')


class AssociationDuMembreMiddleware:
    """Gère l'association active.

    - Utilisateur ordinaire : toujours l'association de sa fiche membre (Membre.utilisateur).
    - Super utilisateur : tant qu'il n'a pas choisi d'association, toute page le renvoie vers
      « Choisir une association » (sinon les pages afficheraient les données sans association).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            if user.is_superuser:
                if not request.session.get('association_id') and not request.path.startswith(ADRESSES_LIBRES):
                    return redirect('choisir_association')
            elif request.session.get('association_fixee_pour') != user.id:
                # La fiche membre n'est relue qu'une fois par session et par utilisateur
                membre = Membre.objects.filter(utilisateur=user).only('association_id').first()
                if membre and membre.association_id:
                    request.session['association_id'] = membre.association_id
                    request.session['association_fixee_pour'] = user.id

        # Code court de l'association (pour que le raccourci installé porte le bon nom et le bon logo)
        request.pwa_code = ''
        if user is not None and user.is_authenticated and not user.is_superuser:
            assoc_id = request.session.get('association_id')
            if assoc_id:
                if 'association_code' not in request.session or request.session.get('association_code_de') != assoc_id:
                    code = Association.objects.filter(pk=assoc_id).values_list('code', flat=True).first()
                    request.session['association_code'] = code or ''
                    request.session['association_code_de'] = assoc_id
                request.pwa_code = request.session.get('association_code', '')
        return self.get_response(request)
