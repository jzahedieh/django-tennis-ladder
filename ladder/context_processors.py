__author__ = 'jon'
from ladder.models import Season


def navigation(request):
    season_list = Season.objects.order_by('-start_date')[:5]
    season_total = Season.objects.count()
    return {'navigation': season_list, 'season_count': season_total}