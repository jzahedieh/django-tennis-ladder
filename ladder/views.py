from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404
from collections import defaultdict

from ladder.models import Season, Ladder, Result


def index(request):
    season_list = Season.objects.order_by('-start_date')
    context = {'season_list': season_list}
    return render(request, 'ladder/index.html', context)


def season(request, season_id):
    season = get_object_or_404(Season, pk=season_id)
    ladders = Ladder.objects.filter(season=season)
    results = Result.objects.filter(ladder__season=season)
    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/season/index.html',
                  {'season': season, 'ladders': ladders, 'results_dict': results_dict})


def ladder(request, ladder_id):
    ladder = get_object_or_404(Ladder, pk=ladder_id)
    return render(request, 'ladder/ladder/index.html', {'ladder': ladder})

