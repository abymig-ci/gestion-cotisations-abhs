"""Connexion par empreinte digitale (WebAuthn / passkey), optionnelle pour chaque utilisateur.

Le téléphone vérifie l'empreinte ; le serveur ne reçoit et ne garde qu'une clé publique.
"""
import base64
import json

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from webauthn import (
    generate_registration_options, verify_registration_response,
    generate_authentication_options, verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria, AuthenticatorAttachment,
    ResidentKeyRequirement, UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)

from .models import EmpreinteAppareil

NOM_SITE = "Gestion des cotisations"


def _b64e(octets):
    return base64.urlsafe_b64encode(octets).rstrip(b'=').decode('ascii')


def _b64d(texte):
    return base64.urlsafe_b64decode(texte + '=' * (-len(texte) % 4))


def _rp_id(request):
    return request.get_host().split(':')[0]


def _origin(request):
    https = request.is_secure() or request.headers.get('x-forwarded-proto') == 'https'
    return f"{'https' if https else 'http'}://{request.get_host()}"


def _corps_json(request):
    try:
        return json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return {}


# ---------- Gestion des appareils (utilisateur connecté) ----------

@login_required
def gerer_empreintes(request):
    return render(request, 'cotisations/empreinte.html', {
        'appareils': request.user.empreintes.all(),
    })


@login_required
@require_POST
def options_enregistrement(request):
    user = request.user
    options = generate_registration_options(
        rp_id=_rp_id(request),
        rp_name=NOM_SITE,
        user_id=str(user.pk).encode(),
        user_name=user.get_username(),
        user_display_name=user.get_full_name() or user.get_username(),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=_b64d(e.credential_id)) for e in user.empreintes.all()
        ],
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    request.session['empreinte_challenge_enreg'] = _b64e(options.challenge)
    return JsonResponse(json.loads(options_to_json(options)))


@login_required
@require_POST
def enregistrer_empreinte(request):
    donnees = _corps_json(request)
    challenge = request.session.pop('empreinte_challenge_enreg', None)
    if not challenge or 'credential' not in donnees:
        return JsonResponse({'ok': False, 'erreur': "Session expirée, recommencez."}, status=400)
    try:
        verifie = verify_registration_response(
            credential=donnees['credential'],
            expected_challenge=_b64d(challenge),
            expected_rp_id=_rp_id(request),
            expected_origin=_origin(request),
            require_user_verification=True,
        )
    except Exception:
        return JsonResponse({'ok': False, 'erreur': "Vérification impossible. Réessayez."}, status=400)

    cred_id = _b64e(verifie.credential_id)
    if EmpreinteAppareil.objects.filter(credential_id=cred_id).exists():
        return JsonResponse({'ok': False, 'erreur': "Cet appareil est déjà enregistré."}, status=400)
    nom = (donnees.get('nom') or '').strip()[:100] or f"Appareil du {timezone.localdate():%d/%m/%Y}"
    EmpreinteAppareil.objects.create(
        utilisateur=request.user,
        credential_id=cred_id,
        cle_publique=_b64e(verifie.credential_public_key),
        compteur=verifie.sign_count,
        nom=nom,
    )
    messages.success(request, "Connexion par empreinte activée sur cet appareil.")
    return JsonResponse({'ok': True})


@login_required
@require_POST
def supprimer_empreinte(request, pk):
    get_object_or_404(EmpreinteAppareil, pk=pk, utilisateur=request.user).delete()
    messages.success(request, "Appareil retiré : la connexion par empreinte est désactivée sur cet appareil.")
    return redirect('empreinte_gerer')


# ---------- Connexion (utilisateur non connecté) ----------

@require_POST
def options_connexion(request):
    options = generate_authentication_options(
        rp_id=_rp_id(request),
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    request.session['empreinte_challenge_conn'] = _b64e(options.challenge)
    return JsonResponse(json.loads(options_to_json(options)))


@require_POST
def connexion_empreinte(request):
    donnees = _corps_json(request)
    challenge = request.session.pop('empreinte_challenge_conn', None)
    credential = donnees.get('credential') or {}
    erreur = JsonResponse({'ok': False, 'erreur': "Empreinte non reconnue. Utilisez votre mot de passe."}, status=400)
    if not challenge or not credential.get('id'):
        return erreur

    appareil = EmpreinteAppareil.objects.select_related('utilisateur').filter(
        credential_id=credential['id']
    ).first()
    if appareil is None or not appareil.utilisateur.is_active:
        return erreur
    try:
        verifie = verify_authentication_response(
            credential=credential,
            expected_challenge=_b64d(challenge),
            expected_rp_id=_rp_id(request),
            expected_origin=_origin(request),
            credential_public_key=_b64d(appareil.cle_publique),
            credential_current_sign_count=appareil.compteur,
            require_user_verification=True,
        )
    except Exception:
        return erreur

    appareil.compteur = verifie.new_sign_count
    appareil.derniere_utilisation = timezone.now()
    appareil.save(update_fields=['compteur', 'derniere_utilisation'])

    user = appareil.utilisateur
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    if user.is_superuser:
        url = reverse('choisir_association')
    else:
        url = donnees.get('next') or ''
        if not url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
            url = settings.LOGIN_REDIRECT_URL
            url = reverse(url) if not url.startswith('/') else url
    return JsonResponse({'ok': True, 'url': url})
