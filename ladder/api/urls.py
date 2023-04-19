from django.urls import include, path
from rest_framework import routers
from ladder.api import views
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView,)

router = routers.DefaultRouter()
router.register('seasons', views.SeasonViewSet)
router.register('players', views.PlayerViewSet, basename='players')
router.register('ladders', views.LadderViewSet)
router.register('leagues', views.LeagueViewSet)
router.register('results', views.ResultPlayerViewSet, basename='result_player')
# router.register('stats', views.StatsViewSet)

urlpatterns = [
    path('token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('ladder/', include(router.urls))
]
