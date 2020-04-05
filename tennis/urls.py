from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
                  path('', include('ladder.urls')),
                  path('admin/', admin.site.urls),
                  path('accounts/login/$', admin.site.login, name='login'),
                  path('api/auth/', include('rest_framework.urls')),
                  path('api/', include('ladder.api.urls')),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
