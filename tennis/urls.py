from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(u'',
	url(ur'^admin/', include(admin.site.urls)),
	url(ur'', include(u'ladder.urls', namespace=u"ladder")),

) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
