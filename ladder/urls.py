from django.conf.urls import url

from ladder import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^list/$', views.list_rounds, name='list'),
    url(r'^current/$', views.current_season_redirect, name='current'),
    # ex: /2013/round/1/
    url(r'^(?P<year>\d+)/round/(?P<season_round>\d+)/$', views.season, name='season'),
    # ex: /2013/round/1/division/1-n
    url(r'^(?P<year>\d+)/round/(?P<season_round>\d+)/division/(?P<division_id>\w+)/$', views.ladder, name='ladder'),
    # ex: /2013/round/1/division/1-n/add/
    url(r'^(?P<year>\d+)/round/(?P<season_round>\d+)/division/(?P<division_id>\w+)/add/$', views.add, name='add'),
    # ex: /head_to_head/1/vs/2
    url(r'^head_to_head/(?P<player_id>\d+)/vs/(?P<opponent_id>\w+)/$', views.head_to_head, name='head_to_head'),
    # ex: /player/1/
    url(r'^player/(?P<player_id>\d+)/$', views.player_history, name='player_history'),
    # ex: /player/
    url(r'^player/search/$', views.player_search, name='player_search'),
    url(r'^player/h2h/(?P<player_id>\d+)/$', views.h2h_search, name='h2h_search'),
    url(r'^player/results/$', views.player_result, name='player_result'),
    url(r'^season/ajax/stats/$', views.season_ajax_stats, name='season_ajax_stats'),
    url(r'^season/ajax/progress/$', views.season_ajax_progress, name='season_ajax_progress'),
]
