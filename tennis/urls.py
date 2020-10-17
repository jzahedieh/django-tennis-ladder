from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

admin.autodiscover()

urlpatterns = [
                  path('', include('ladder.urls')),
                  path('accounts/', include('django.contrib.auth.urls')),
                  path('admin/', admin.site.urls),
                  path('api/auth/', include('rest_framework.urls')),
                  path('api/', include('ladder.api.urls')),
                  path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
                  path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
