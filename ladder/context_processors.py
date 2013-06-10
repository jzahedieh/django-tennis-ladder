__author__ = 'jon'
from ladder.models import Season


def navigation(request):
    season_list = Season.objects.order_by('-start_date')
    return {'navigation': season_list}