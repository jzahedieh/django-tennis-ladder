from django.urls import include, path
from rest_framework import routers
from ladder.api import views

router = routers.DefaultRouter()
router.register('seasons', views.SeasonViewSet)
router.register('players', views.PlayerViewSet)
router.register('ladders', views.LadderViewSet)
router.register('leagues', views.LeagueViewSet)
router.register('results', views.ResultViewSet)

urlpatterns = [
    path('ladder/', include(router.urls))
]
