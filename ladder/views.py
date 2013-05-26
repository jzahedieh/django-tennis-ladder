from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpRequest
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from ladder.models import Ladder, Player, Result
from django.contrib.auth.decorators import login_required
import datetime, json
from collections import defaultdict



def multi_dimensions(n, type):
  """ Creates an n-dimension dictionary where the n-th dimension is of type 'type'
  """
  if n<=1:
    return type()
  return defaultdict(lambda:multi_dimensions(n-1, type))



from ladder.models import Season, Ladder, Result


def index(request):
    season_list = Season.objects.order_by('-start_date')
    context = {'season_list': season_list}
    return render(request, 'ladder/index.html', context)


def season(request, season_id):
    season = get_object_or_404(Season, pk=season_id)
    ladders = Ladder.objects.filter(season=season)
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
    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/season/index.html',
                  dict(season=season, ladders=ladders, results_dict=results_dict)
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
    players = ladder.players.all()
    unplayed_matches = defaultdict(lambda:defaultdict(list))

    for player in players:
        player_dict = {player: ladder.players.all()}
        player_dict[player] = player_dict[player].exclude(first_name=player.first_name, last_name=player.last_name)
        for result in ladder.result_set.filter(player=player):
            player_dict[player] = player_dict[player].exclude(first_name=result.opponent.first_name, last_name=result.opponent.last_name)

        for opponent in player_dict[player].all():
            unplayed_matches[player.id][opponent.id] = {'first_name': opponent.first_name, 'last_name': opponent.last_name}

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

        player_result_add = Result(ladder=ladder, player=player_object, opponent=opponent_object, result=int(player_score), date_added=datetime.date.today())
        opponent_result_add = Result(ladder=ladder, opponent=player_object, player=opponent_object, result=int(opponent_score), date_added=datetime.date.today())
        player_result_add.save()
        opponent_result_add.save()
    except Exception as e:
        return render(request, 'ladder/ladder/add.html', {
            'ladder': ladder,
            'error_message': e,
            'points': range(10)
        })
        #return HttpResponseRedirect(reverse('ladder:add', args=(ladder.id,)))
    else:
        return HttpResponseRedirect(reverse('ladder:add', args=(ladder.id,)))
