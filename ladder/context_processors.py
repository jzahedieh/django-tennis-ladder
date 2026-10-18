from ladder.models import Season, Player
from django.conf import settings


def navigation(request):
    """
    Generates the urls for the top navigation
    """
    published_seasons = Season.objects.filter(is_draft=False).order_by('-start_date')
    season_list = published_seasons[1:5]
    season_first = published_seasons.first()
    season_total = published_seasons.count()

    nav_player = None
    if getattr(request, 'user', None) and request.user.is_authenticated:
        nav_player = Player.objects.filter(user=request.user).first()

    return {
        'navigation': season_list,
        'season_count': season_total,
        'season_first': season_first,
        'nav_player': nav_player,
    }


def umami_context(request):
    return {
        'umami_website_id': getattr(settings, 'UMAMI_WEBSITE_ID', ''),
    }
