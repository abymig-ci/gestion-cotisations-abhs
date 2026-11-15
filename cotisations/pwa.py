"""Installation sur l'écran d'accueil (PWA) : version générale et version propre à chaque association."""
import base64
import io
import os
from functools import lru_cache

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from .connexion import ConnexionView
from .models import Association, Parametre

NOM_APP = "Gestcotis"
COULEUR = "#0a1c5c"
TAILLES_AUTORISEES = (180, 192, 512)


# ------------------------------------------------------------------ manifeste
def _reponse_manifeste(donnees):
    reponse = JsonResponse(donnees, json_dumps_params={"ensure_ascii": False})
    reponse["Content-Type"] = "application/manifest+json; charset=utf-8"
    return reponse


def manifest(request):
    """Raccourci général (super utilisateur) : adresse du site, icône = logo de l'application."""
    return _reponse_manifeste({
        "id": "/",
        "name": NOM_APP,
        "short_name": NOM_APP,
        "description": "Gestion des membres et des cotisations",
        "start_url": "/login/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#ffffff",
        "theme_color": COULEUR,
        "lang": "fr",
        "icons": [
            {"src": "/pwa/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/pwa/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/pwa/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    })


def _association_active(code):
    return get_object_or_404(Association, code=code, est_active=True)


def manifest_association(request, code):
    """Raccourci d'une association : nom Gestcotis-<code>, icône = logo de l'association."""
    assoc = _association_active(code)
    param = Parametre.objects.filter(association=assoc).first()
    couleur = (param.couleur_principale if param else assoc.couleur_principale) or COULEUR
    nom = f"{NOM_APP}-{assoc.code}"
    return _reponse_manifeste({
        "id": f"/a/{assoc.code}/",
        "name": nom,
        "short_name": nom,
        "description": f"Gestion des cotisations - {assoc.nom}",
        "start_url": f"/a/{assoc.code}/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#ffffff",
        "theme_color": couleur,
        "lang": "fr",
        "icons": [
            {"src": f"/pwa/{assoc.code}/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": f"/pwa/{assoc.code}/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": f"/pwa/{assoc.code}/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    })


# ------------------------------------------------------------ service worker
SERVICE_WORKER = """
// Service worker minimal : requis pour proposer l'installation. Il ne met rien en cache,
// l'application reste toujours à jour et les données ne sont jamais servies depuis un cache.
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function () { /* le navigateur gère la requête normalement */ });
"""


def service_worker(request):
    reponse = HttpResponse(SERVICE_WORKER, content_type="application/javascript; charset=utf-8")
    reponse["Service-Worker-Allowed"] = "/"
    reponse["Cache-Control"] = "no-cache"
    return reponse


# -------------------------------------------------------------------- icônes
def generer_icone(source_logo, taille, marge):
    """Logo (chemin ou fichier en mémoire) centré dans un carré blanc de `taille` pixels."""
    from PIL import Image, ImageDraw

    fond = Image.new("RGBA", (taille, taille), (255, 255, 255, 255))
    try:
        logo = Image.open(source_logo).convert("RGBA")
    except Exception:
        # Logo introuvable : carré aux couleurs de l'application avec une pastille blanche
        dessin = ImageDraw.Draw(fond)
        dessin.rectangle([0, 0, taille, taille], fill=COULEUR)
        m = int(taille * 0.25)
        dessin.ellipse([m, m, taille - m, taille - m], fill=(255, 255, 255, 255))
        sortie = io.BytesIO()
        fond.convert("RGB").save(sortie, "PNG")
        return sortie.getvalue()

    zone = int(taille * (1 - 2 * marge))
    logo.thumbnail((zone, zone), Image.LANCZOS)
    fond.alpha_composite(logo, ((taille - logo.width) // 2, (taille - logo.height) // 2))
    sortie = io.BytesIO()
    fond.convert("RGB").save(sortie, "PNG", optimize=True)
    return sortie.getvalue()


def _logo_depuis_base64(valeur):
    """Fichier en mémoire à partir d'un logo enregistré en base64 (data:image/png;base64,...)."""
    if not valeur:
        return None
    try:
        donnees = valeur.split(",", 1)[1] if valeur.startswith("data:") else valeur
        return io.BytesIO(base64.b64decode(donnees))
    except Exception:
        return None


def _chemin_logo_general():
    return os.path.join(settings.BASE_DIR, "static", "img", "logo.png")


@lru_cache(maxsize=8)
def _icone_generale(taille, marge):
    return generer_icone(_chemin_logo_general(), taille, marge)


def _png(contenu):
    reponse = HttpResponse(contenu, content_type="image/png")
    reponse["Cache-Control"] = "public, max-age=3600"
    return reponse


def _controler(taille):
    if taille not in TAILLES_AUTORISEES:
        raise Http404


def icone(request, taille):
    _controler(taille)
    return _png(_icone_generale(taille, 0.08))


def icone_maskable(request, taille):
    # Marge plus grande : Android découpe l'icône en cercle ou en carré arrondi
    _controler(taille)
    return _png(_icone_generale(taille, 0.22))


def _icone_association(code, taille, marge):
    _controler(taille)
    assoc = _association_active(code)
    param = Parametre.objects.filter(association=assoc).first()
    source = _logo_depuis_base64(param.logo_base64 if param else None) or _chemin_logo_general()
    return _png(generer_icone(source, taille, marge))


def icone_association(request, code, taille):
    return _icone_association(code, taille, 0.08)


def icone_association_maskable(request, code, taille):
    return _icone_association(code, taille, 0.22)


# ------------------------------------------- page de connexion d'une association
class AccueilAssociationView(ConnexionView):
    """Page de connexion aux couleurs d'une association : /a/<code>/ (c'est le lien envoyé aux membres)."""

    def dispatch(self, request, *args, **kwargs):
        self.association = _association_active(kwargs["code"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        param = Parametre.objects.filter(association=self.association).first()
        contexte.update({
            "pwa_code": self.association.code,
            "accueil_nom": (param.nom_association if param and param.nom_association else self.association.nom),
            "accueil_logo": param.logo_base64 if param and param.logo_base64 else None,
        })
        return contexte
