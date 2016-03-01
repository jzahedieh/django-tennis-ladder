from django.conf.urls import include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
                  url(ur'^admin/', include(admin.site.urls)),
                  url(ur'', include(u'ladder.urls', namespace="ladder")),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
