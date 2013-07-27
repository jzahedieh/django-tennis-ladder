from django.conf.urls import patterns, url

from ladder import views

urlpatterns = patterns('',
                       url(r'^$', views.index, name='index'),
                       url(r'^list/$', views.list, name='list'),
                       # want: /summer-2013/
                       url(r'^(?P<slug>[-\w]+)/$', views.season, name='season'),
                       # want: /summer-2013/division/1-n/
                       url(r'^(?P<slug>[-\w]+)/division/(?P<divison_id>\d+)/$', views.ladder, name='ladder'),
                       url(r'^add/(?P<ladder_id>\d+)$', views.add, name='add'),
                       url(r'^add_result/(?P<ladder_id>\d+)$', views.add_result, name='add_result'),
)
