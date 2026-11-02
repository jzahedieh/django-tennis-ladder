from django.urls import path

from ladder import views

urlpatterns = [
    path('', views.index, name='index'),
    path('stats/', views.stats, name='stats'),
    path('list/', views.list_rounds, name='list'),
    path('current/', views.current_season_redirect, name='current'),
    path('<int:year>/round/<int:season_round>/', views.season, name='season'),
    path('<int:year>/round/<int:season_round>/division/<int:division_id>/', views.ladder, name='ladder'),
    path('<int:year>/round/<int:season_round>/division/<int:division_id>/add/', views.add, name='add'),
    path('<int:year>/round/<int:season_round>/division/<int:division_id>/subscription/', views.ladder_subscription, name='ladder_subscription'),
    path('head_to_head/<int:player_id>/vs/<int:opponent_id>/', views.head_to_head, name='head_to_head'),
    path('player/<int:player_id>/', views.player_history, name='player_history'),
    path('player/search/', views.player_search, name='player_search'),
    path('player/results/', views.player_result, name='player_result'),
    path('account/', views.account, name='account'),
    path('result/entry/', views.result_entry, name='result_entry'),
    path('result/entry/add/', views.result_entry_add, name='result_entry_add'),
    path('result/entry/<str:pair_key>/edit/', views.result_entry_edit, name='result_entry_edit'),
    path('result/entry/<str:pair_key>/delete/', views.result_entry_delete, name='result_entry_delete'),
    path('unsubscribe/<uuid:token>/', views.unsubscribe_token, name='unsubscribe_token'),
]
