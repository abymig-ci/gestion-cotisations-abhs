"""Installation de l'application sur l'écran d'accueil (PWA) : manifeste, service worker et icônes."""
import io
import os
from functools import lru_cache

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse

NOM_APP = "Gestcotis"
COULEUR = "#0a1c5c"
TAILLES_AUTORISEES = (180, 192, 512)


def manifest(request):
    donnees = {
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
    }
    reponse = JsonResponse(donnees, json_dumps_params={"ensure_ascii": False})
    reponse["Content-Type"] = "application/manifest+json; charset=utf-8"
    return reponse


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


def generer_icone(chemin_logo, taille, marge):
    """Logo centré dans un carré blanc de `taille` pixels, avec une marge (en proportion)."""
    from PIL import Image, ImageDraw

    fond = Image.new("RGBA", (taille, taille), (255, 255, 255, 255))
    try:
        logo = Image.open(chemin_logo).convert("RGBA")
    except Exception:
        # Logo introuvable : carré aux couleurs de l'association avec une pastille blanche
        dessin = ImageDraw.Draw(fond)
        dessin.rectangle([0, 0, taille, taille], fill=COULEUR)
        m = int(taille * 0.25)
        dessin.ellipse([m, m, taille - m, taille - m], fill=(255, 255, 255, 255))
        sortie = io.BytesIO()
        fond.convert("RGB").save(sortie, "PNG")
        return sortie.getvalue()

    zone = int(taille * (1 - 2 * marge))
    logo.thumbnail((zone, zone), Image.LANCZOS)
    x = (taille - logo.width) // 2
    y = (taille - logo.height) // 2
    fond.alpha_composite(logo, (x, y))
    sortie = io.BytesIO()
    fond.convert("RGB").save(sortie, "PNG", optimize=True)
    return sortie.getvalue()


@lru_cache(maxsize=8)
def _icone_en_cache(taille, marge):
    chemin = os.path.join(settings.BASE_DIR, "static", "img", "logo.png")
    return generer_icone(chemin, taille, marge)


def _repondre(taille, marge):
    if taille not in TAILLES_AUTORISEES:
        raise Http404
    reponse = HttpResponse(_icone_en_cache(taille, marge), content_type="image/png")
    reponse["Cache-Control"] = "public, max-age=86400"
    return reponse


def icone(request, taille):
    return _repondre(taille, 0.08)


def icone_maskable(request, taille):
    # Marge plus grande : Android découpe l'icône en cercle ou en carré arrondi
    return _repondre(taille, 0.22)
