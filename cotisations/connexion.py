from django.contrib.auth.views import LoginView
from django.shortcuts import resolve_url


class ConnexionView(LoginView):
    """Page d'accueil avec formulaire de connexion.

    - Le super utilisateur est toujours envoyé sur « Choisir une association ».
    - Les autres utilisateurs vont là où ils allaient avant (paramètre ?next=, sinon LOGIN_REDIRECT_URL).
    """
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.is_superuser:
            return resolve_url('choisir_association')
        return super().get_success_url()
