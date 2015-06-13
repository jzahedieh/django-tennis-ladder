from django.conf.urls import patterns, url

from ladder import views

urlpatterns = patterns('',
                       url(ur'^$', views.index, name='index'),
                       url(ur'^list/$', views.list_rounds, name='list'),
                       # ex: /2013/round/1/
                       url(ur'^(?P<year>\d+)/round/(?P<season_round>\d+)/$', views.season, name='season'),
                       # ex: /2013/round/1/division/1-n
                       url(ur'^(?P<year>\d+)/round/(?P<season_round>\d+)/division/(?P<division_id>\w+)/$', views.ladder, name='ladder'),
                       # ex: /2013/round/1/division/1-n/add/
                       url(ur'^(?P<year>\d+)/round/(?P<season_round>\d+)/division/(?P<division_id>\w+)/add/$', views.add, name='add'),
                       # ex: /head_to_head/1/vs/2
                       url(ur'^head_to_head/(?P<player_id>\d+)/vs/(?P<opponent_id>\w+)/$', views.head_to_head, name='head_to_head'),
                       # ex: /player/1/
                       url(ur'^player/(?P<player_id>\d+)/$', views.player_history, name='player_history'),
                       # ex: /player/
                       url(ur'^player/search/$', views.player_search, name='player_search'),
                       url(ur'^player/h2h/(?P<player_id>\d+)/$', views.h2h_search, name='h2h_search'),
                       url(ur'^player/results/$', views.player_result, name='player_result'),
                       url(ur'^season/ajax/stats/$', views.season_ajax_stats, name='season_ajax_stats'),
                       url(ur'^season/ajax/progress/$', views.season_ajax_progress, name='season_ajax_progress'),
)
