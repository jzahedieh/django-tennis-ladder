from django.conf.urls import patterns, url

from ladder import views

urlpatterns = patterns('',
                       # ex: /ladder/
                       url(r'^$', views.index, name='index'),
                       # want: /summer-2013/
                       url(r'^(?P<slug>[-\w]+)/$', views.season, name='season'),
                       # ex: /ladder/ladder/5/
                       # want: /season/summer-2013/ladder/1-13/
                       url(r'^ladder/(?P<ladder_id>\d+)$', views.ladder, name='ladder'),
                       url(r'^add/(?P<ladder_id>\d+)$', views.add, name='add'),
                       url(r'^add_result/(?P<ladder_id>\d+)$', views.add_result, name='add_result'),
)
