from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from cotisations.connexion import ConnexionView
from cotisations import pwa
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', ConnexionView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', include('cotisations.urls_libres')),
    path('', include('cotisations.urls_empreinte')),
    path('', include('cotisations.urls')),
    path('membres/', include('membres.urls')),
    path('depenses/', include('depenses.urls')),
    path('pwa/manifest.json', pwa.manifest, name='pwa_manifest'),
    path('pwa/service-worker.js', pwa.service_worker, name='pwa_service_worker'),
    path('pwa/icon-<int:taille>.png', pwa.icone, name='pwa_icone'),
    path('pwa/icon-maskable-<int:taille>.png', pwa.icone_maskable, name='pwa_icone_maskable'),
    path('au-revoir/', pwa.au_revoir, name='au_revoir'),
    path('a/<slug:code>/', pwa.AccueilAssociationView.as_view(), name='accueil_association'),
    path('pwa/<slug:code>/manifest.json', pwa.manifest_association, name='pwa_manifest_association'),
    path('pwa/<slug:code>/icon-<int:taille>.png', pwa.icone_association, name='pwa_icone_association'),
    path('pwa/<slug:code>/icon-maskable-<int:taille>.png', pwa.icone_association_maskable, name='pwa_icone_association_maskable'),
]

# Configuration pour servir les fichiers médias (uploads) en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
