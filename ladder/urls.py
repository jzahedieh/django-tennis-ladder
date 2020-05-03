from django.urls import re_path

from ladder import views

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'^list/$', views.list_rounds, name='list'),
    re_path(r'^current/$', views.current_season_redirect, name='current'),
    # ex: /2013/round/1/
    re_path(r'^(?P<year>\d+)/round/(?P<season_round>\d+)/$', views.season, name='season'),
    # ex: /2013/round/1/division/1-n
    re_path(r'^(?P<year>\d+)/round/(?P<season_round>\d+)/division/(?P<division_id>\w+)/$', views.LeagueView.as_view(), name='ladder'),
    # ex: /2013/round/1/division/1-n/add/
    re_path(r'^(?P<year>\d+)/round/(?P<season_round>\d+)/division/(?P<division_id>\w+)/add/$', views.add, name='add'),
    # ex: /head_to_head/1/vs/2
    re_path(r'^head_to_head/(?P<player_id>\d+)/vs/(?P<opponent_id>\w+)/$', views.head_to_head, name='head_to_head'),
    # ex: /player/1/
    re_path(r'^player/(?P<player_id>\d+)/$', views.player_history, name='player_history'),
    # ex: /player/
    re_path(r'^player/search/$', views.player_search, name='player_search'),
    re_path(r'^player/h2h/(?P<player_id>\d+)/$', views.h2h_search, name='h2h_search'),
    re_path(r'^player/results/$', views.player_result, name='player_result'),
    re_path(r'^season/ajax/stats/$', views.season_ajax_stats, name='season_ajax_stats'),
    re_path(r'^season/ajax/progress/$', views.season_ajax_progress, name='season_ajax_progress'),
]
