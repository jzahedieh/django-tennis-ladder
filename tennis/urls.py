from django.urls import include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
                  re_path(r'^admin/', admin.site.urls),
                  re_path(r'^accounts/login/$', admin.site.login, name='login'),
                  re_path(r'', include('ladder.urls')),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
