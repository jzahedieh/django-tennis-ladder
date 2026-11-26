from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

from api.api import api as ninja_api

admin.autodiscover()

urlpatterns = [
    path('v1/', ninja_api.urls),
    path('', include('ladder.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path(f'{settings.ADMIN_URL}/', admin.site.urls),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
