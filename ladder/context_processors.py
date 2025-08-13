from ladder.models import Season
from django.conf import settings


def navigation(request):
    """
    Generates the urls for the top navigation
    """
    season_list = Season.objects.order_by('-start_date')[1:5]
    season_first = Season.objects.latest('start_date')
    season_total = Season.objects.count()
    return {'navigation': season_list, 'season_count': season_total, 'season_first': season_first}


def umami_context(request):
    return {
        'umami_website_id': getattr(settings, 'UMAMI_WEBSITE_ID', ''),
    }
