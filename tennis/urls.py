from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
	url(r'^admin/', include(admin.site.urls)),
	url(r'', include('ladder.urls', namespace="ladder")),

) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
