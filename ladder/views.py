from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.views.decorators.cache import cache_page
from ladder.models import Ladder, Player, Result, Season, League
from django.contrib.auth.decorators import login_required
import datetime, json
from collections import defaultdict
from decimal import Decimal



def multi_dimensions(n, type):
  """ Creates an n-dimension dictionary where the n-th dimension is of type 'type'
  """
  if n<=1:
    return type()
  return defaultdict(lambda:multi_dimensions(n-1, type))


@cache_page(60 * 60 * 12)  # 12 hour page cache
def index(request):
    current_season = Season.objects.order_by('-start_date')[0]
    context = {
        'current_season': current_season,
    }
    return render(request, 'ladder/index.html', context)


@cache_page(60 * 60 * 12)  # 12 hour page cache
def season(request, slug):
    try:
        season = Season.objects.get(slug=slug)
    except Season.DoesNotExist:
        raise Http404

    ladders = Ladder.objects.filter(season=season)
    #ladders = Result.objects.filter(season=group__ladder)
    # season_before_date = season.start_date - datetime.timedelta(days=31)
    # prev_results_dict = {}
    # try:
    #     prev_season = Season.objects.get(start_date__lte=season_before_date, end_date__gte=season_before_date)
    #     prev_results = Result.objects.filter(ladder__season=prev_season)
    #     for result in prev_results:
    #         try:
    #             result_count = prev_results_dict[result.player_id]['total']
    #             played_count = prev_results_dict[result.player_id]['played']
    #             won_count = prev_results_dict[result.player_id]['won']
    #             if result.result == 9:
    #                 prev_results_dict[result.player_id] = {
    #                     'div': result.ladder.division,
    #                     'total': result_count + (result.result + 1 + 2),
    #                     'played': (played_count + 1),
    #                     'won': (won_count + 1)
    #                 }
    #             else:
    #                 prev_results_dict[result.player_id] = {
    #                     'div': result.ladder.division,
    #                     'total': result_count + (result.result + 1),
    #                     'played': (played_count + 1),
    #                     'won': won_count
    #                 }
    #         except KeyError:
    #             if result.result == 9:
    #                 prev_results_dict[result.player_id] = {
    #                     'div': result.ladder.division,
    #                     'total': (result.result + 1 + 2),
    #                     'played': 1,
    #                     'won': 1
    #                 }
    #             else:
    #                 prev_results_dict[result.player_id] = {
    #                     'div': result.ladder.division,
    #                     'total': (result.result + 1),
    #                     'played': 1,
    #                     'won': 0
    #                 }
    # except season.DoesNotExist:
    #     pass

    results = Result.objects.filter(ladder__season=season)
    league = League.objects.filter(ladder__season=season)


    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/season/index.html',
                  dict(season=season, ladders=ladders, results_dict=results_dict, league=league)
    )

    return render(request, 'ladder/season/index.html',
                  dict(season=season, ladders=ladders, results_dict=results_dict, prev_results_dict=prev_results_dict)
    )


def ladder(request, ladder_id):
    ladder = get_object_or_404(Ladder, pk=ladder_id)

    results = Result.objects.filter(ladder=ladder)

    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/ladder/index.html', {'ladder': ladder, 'results_dict': results_dict})

@login_required
def add(request, ladder_id):
    ladder = get_object_or_404(Ladder, pk=ladder_id)

    results = Result.objects.filter(ladder=ladder)

    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/ladder/add.html', {'ladder': ladder, 'results_dict': results_dict, 'points': range(10)})

    return render(request, 'ladder/ladder/add.html', {'ladder': ladder, 'points': range(10), 'unplayed_matches': json.dumps(unplayed_matches)})

@login_required
def add_result(request, ladder_id):
    ladder = get_object_or_404(Ladder, pk=ladder_id)
    try:
        player_object = Player.objects.get(id=request.POST['player'])
        opponent_object = Player.objects.get(id=request.POST['opponent'])
        player_score = request.POST['player_score']
        opponent_score = request.POST['opponent_score']

        if int(player_score) != 9 and int(opponent_score) != 9:
            raise Exception("No winner selected")

        if int(player_score) == 9 and int(opponent_score) == 9:
            raise Exception("Can't have two winners")

        # player_result_add = Result(ladder=ladder, player=player_object, opponent=opponent_object, result=int(player_score), date_added=datetime.date.today())
        # opponent_result_add = Result(ladder=ladder, opponent=player_object, player=opponent_object, result=int(opponent_score), date_added=datetime.date.today())
        # player_result_add.save()
        # opponent_result_add.save()
        try:
            result_object = Result.objects.get(ladder=ladder, player=player_object, opponent=opponent_object)
            result_object.delete()
            raise Exception("want to add all the time")
        except:
            player_result_object = Result(ladder=ladder, player=player_object, opponent=opponent_object,
                                       result=player_score, date_added=datetime.datetime.now())
            player_result_object.save()


        try:
            result_object = Result.objects.get(ladder=ladder, player=opponent_object, opponent=player_object)
            result_object.delete()
            raise Exception("want to add all the time")
        except:
            opp_result_object = Result(ladder=ladder, player=opponent_object, opponent=player_object,
                                       result=opponent_score, date_added=datetime.datetime.now())
            opp_result_object.save()


    except Exception as e:
        return render(request, 'ladder/ladder/add.html', {
            'ladder': ladder,
            'error_message': e,
            'points': range(10)
        })
        #return HttpResponseRedirect(reverse('ladder:add', args=(ladder.id,)))
    else:
        return HttpResponseRedirect(reverse('ladder:add', args=(ladder.id,)))
