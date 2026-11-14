from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from cotisations.connexion import ConnexionView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', ConnexionView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', include('cotisations.urls')),
    path('membres/', include('membres.urls')),
    path('depenses/', include('depenses.urls')),
]

# Configuration pour servir les fichiers médias (uploads) en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
