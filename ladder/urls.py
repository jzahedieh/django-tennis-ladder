from django.conf.urls import patterns, url

from ladder import views

urlpatterns = patterns('',
                       # ex: /ladder/
                       url(r'^$', views.index, name='index'),
                       # ex: /ladder/season/5/
                       url(r'^season/(?P<season_id>\d+)$', views.season, name='season'),
                       # ex: /ladder/ladder/5/
                       url(r'^ladder/(?P<ladder_id>\d+)$', views.ladder, name='ladder'),
                       url(r'^add/(?P<ladder_id>\d+)$', views.add, name='add'),
                       url(r'^add_result/(?P<ladder_id>\d+)$', views.add_result, name='add_result'),
)
