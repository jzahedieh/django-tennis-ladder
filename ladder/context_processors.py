__author__ = u'jon'
from ladder.models import Season


def navigation(request):
    u"""
    Generates the urls for the top navigation
    """
    season_list = Season.objects.order_by(u'-start_date')[1:5]
    season_first = Season.objects.latest(u'start_date')
    season_total = Season.objects.count()
    return {u'navigation': season_list, u'season_count': season_total, u'season_first':season_first}