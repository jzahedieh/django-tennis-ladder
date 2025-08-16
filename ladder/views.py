import datetime
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Max
from django.http import HttpResponseRedirect, Http404, HttpResponse, HttpResponseForbidden, JsonResponse, \
    HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from ladder.forms import AddResultForm, AddEntryForm
from ladder.models import Ladder, Player, Result, Season, League, LadderSubscription

def _unplayed_opponents_for(user_player, ladder):
    # players in this ladder, in ladder order
    league_players = [l.player for l in ladder.league_set.select_related('player').all()]
    # all pairings already played (either direction)
    played_pairs = set()
    for r in Result.objects.filter(ladder=ladder).values_list('player_id', 'opponent_id'):
        played_pairs.add(tuple(sorted(r)))
    # opponents the user hasn't played yet, in league (sort_order) order
    unplayed = []
    for p in league_players:
        if p.id == user_player.id:
            continue
        pair = tuple(sorted((user_player.id, p.id)))
        if pair not in played_pairs:
            unplayed.append(p)
    return unplayed

def index(request):
    current_season = Season.objects.filter(is_draft=False).latest('start_date')
    os_year = Season.objects.order_by('start_date')[0].start_date.year
    cs_year = current_season.start_date.year

    at_ladders = Season.objects.count()
    at_divisions = Ladder.objects.count()
    at_results = int(Result.objects.count() / 2)
    at_players = Player.objects.count()

    context = {
        'current_season': current_season,
        'at_years': (cs_year - os_year),
        'at_years_str': ' (' + os_year.__str__() + ' -> ' + cs_year.__str__() + ')',
        'at_divisions': at_divisions,
        'at_ladders': at_ladders,
        'at_results': at_results,
        'at_players': at_players,
    }
    return render(request, 'ladder/index.html', context)


def list_rounds(request):
    seasons = Season.objects.filter(is_draft=False).order_by('-start_date')
    context = {
        'seasons': seasons,
    }
    return render(request, 'ladder/season/list.html', context)


def current_season_redirect(request):
    season_first = Season.objects.filter(is_draft=False).latest('start_date')

    return HttpResponseRedirect(reverse('season', args=(
        season_first.start_date.year, season_first.season_round)
    ))


def season(request, year, season_round):
    season_object = get_object_or_404(Season, start_date__year=year, season_round=season_round)

    if season_object.is_draft and not request.user.is_superuser:
        prev = (Season.objects
                .filter(is_draft=False, start_date__lt=season_object.start_date)
                .order_by('-start_date')
                .first())
        if prev:
            return HttpResponseRedirect(reverse('season', args=(prev.start_date.year, prev.season_round)))
        raise Http404  # no published season to show

    # Optimize with prefetch_related to avoid N+1 queries
    ladders = Ladder.objects.filter(season=season_object).prefetch_related(
        'league_set__player__user'  # Prefetch leagues, players, and users
    )

    # Get all results for this season with related data in one query
    results = Result.objects.filter(
        ladder__season=season_object
    ).select_related(
        'player', 'opponent', 'ladder'
    )

    # Build results dictionary efficiently
    results_dict = {}
    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    # No need to fetch league separately as it's prefetched
    return render(
        request, 'ladder/season/index.html',
        dict(season=season_object, ladders=ladders, results_dict=results_dict)
    )


def ladder(request, year, season_round, division_id):
    ladder_object = get_object_or_404(
        Ladder.objects.filter(season__is_draft=False).prefetch_related('league_set__player__user'),
        division=division_id,
        season__start_date__year=year,
        season__season_round=season_round
    )

    subscribed = False
    if request.user.is_authenticated and not request.user.is_superuser:
        subscribed = LadderSubscription.objects.filter(
            user=request.user,
            ladder__division=division_id,
            ladder__season__start_date__year=year,
            ladder__season__season_round=season_round
        ).exists()  # Use exists() instead of count() > 0

    # Optimize results query with select_related
    results = Result.objects.filter(ladder=ladder_object).select_related(
        'player', 'opponent'
    )

    results_dict = {}
    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/ladder/index.html',
                  {'ladder': ladder_object, 'results_dict': results_dict, 'subscribed': subscribed})

@login_required
@never_cache
def ladder_subscription(request, year, season_round, division_id):

    if request.user.is_superuser or not request.user.is_authenticated:
        return HttpResponseForbidden()

    existing_subscription = LadderSubscription.objects.filter(
        user=request.user,
        ladder__division=division_id,
        ladder__season__start_date__year=year,
        ladder__season__season_round=season_round,
        ladder__season__is_draft=False,
    )

    # unsubscribe
    if existing_subscription.count() > 0:
        existing_subscription.delete()
        messages.success(request, 'Unsubscribed from email notifications.')
        return HttpResponseRedirect(reverse('ladder', args=(year, season_round, division_id)))

    ladder_object = get_object_or_404(
        Ladder,
        division=division_id,
        season__start_date__year=year,
        season__season_round=season_round,
        season__is_draft=False,
    )

    # subscribe
    LadderSubscription(
        user=request.user,
        ladder=ladder_object,
        subscribed_at=datetime.datetime.now()
    ).save()

    messages.success(request, 'Subscribed to email notifications.')
    return HttpResponseRedirect(reverse('ladder', args=(year, season_round, division_id)))

@login_required
def add(request, year, season_round, division_id):
    if not request.user.is_superuser:
        return HttpResponseRedirect(reverse('ladder', args=(year, season_round, division_id)))

    ladder_object = get_object_or_404(
        Ladder,
        division=division_id,
        season__start_date__year=year,
        season__season_round=season_round,
        season__is_draft=False,
    )

    result = Result(ladder=ladder_object, date_added=datetime.datetime.now())

    try:
        next_ladder = Ladder.objects.get(season=ladder_object.season, division=ladder_object.division + 1)
    except Ladder.DoesNotExist:
        next_ladder = False

    try:
        previous_ladder = Ladder.objects.get(season=ladder_object.season, division=ladder_object.division - 1)
    except Ladder.DoesNotExist:
        previous_ladder = False


    # process or generate te score adding form
    if request.POST:
        form = AddResultForm(ladder_object, request.POST, instance=result)
        if form.is_valid():
            losing_result = form.save(commit=False)

            # check for existing results, assume update if find a match aka delete
            try:
                existing_player_result = Result.objects.get(ladder=ladder_object, player=losing_result.player,
                                                            opponent=losing_result.opponent)
                existing_player_result.delete()
                existing_opponent_result = Result.objects.get(ladder=ladder_object, player=losing_result.opponent,
                                                              opponent=losing_result.player)
                existing_opponent_result.delete()
            except Result.DoesNotExist:
                pass

            # build the mirror result (aka winner) from losing form data
            winning_result = Result(ladder=losing_result.ladder, player=losing_result.opponent,
                                    opponent=losing_result.player, result=9, date_added=losing_result.date_added,
                                    inaccurate_flag=losing_result.inaccurate_flag)
            losing_result.save()
            winning_result.save()

            return HttpResponseRedirect(reverse('add', args=(
                ladder_object.season.start_date.year, ladder_object.season.season_round, ladder_object.division)))
    else:
        form = AddResultForm(ladder_object, instance=result)

    # prepare the results for displaying
    results = Result.objects.filter(ladder=ladder_object)
    results_dict = {}
    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/ladder/add.html',
                  {'ladder': ladder_object, 'results_dict': results_dict, 'form': form,
                   'next_ladder': next_ladder, 'previous_ladder': previous_ladder})


def player_history(request, player_id):
    player = get_object_or_404(Player, pk=player_id)

    # Prefetch player results at the player level
    player = Player.objects.prefetch_related('result_player').get(pk=player_id)

    # Get league_set with comprehensive prefetching
    league_set = player.league_set.select_related(
        'ladder__season'
    ).prefetch_related(
        'ladder__league_set'  # For league counts
    ).order_by('-ladder__season__start_date')

    # Force evaluation of league_set to ensure prefetching works
    league_list = list(league_set)

    # Pre-calculate player stats
    player_stats = player.player_stats()

    # Return top 10 played against
    try:
        head = Result.objects.values('opponent', 'opponent__first_name', 'opponent__last_name').filter(
            player=player).annotate(times_played=Count('opponent'), last_played=Max('date_added')).order_by(
            '-times_played')[:10]
    except Result.DoesNotExist:
        raise Http404

    return render(request, 'ladder/player/history.html', {
        'player': player,
        'league_set': league_list,  # Use the evaluated list
        'ladder_set': league_list,
        'head': head,
        'player_stats': player_stats
    })


def head_to_head(request, player_id, opponent_id):
    player = get_object_or_404(Player, pk=player_id)
    opponent = get_object_or_404(Player, pk=opponent_id)

    results1 = Result.objects.filter(player=player, opponent=opponent, result__lt=9).order_by(
        '-ladder__season__end_date')
    results2 = Result.objects.filter(player=opponent, opponent=player, result__lt=9).order_by(
        '-ladder__season__end_date')

    results = results1 | results2

    stats = {'won': results2.count(), 'lost': results1.count(), 'played': results1.count() + results2.count()}

    return render(request, 'ladder/head_to_head/index.html',
                  {'stats': stats, 'results': results, 'player': player, 'opponent': opponent})


def player_result(request):
    query = request.GET.get('player_name', '').strip()
    if not query:
        raise Http404

    terms = query.split()
    qs = Player.objects.all()

    if request.user.is_authenticated:
        # Member view: allow first or last name search
        for term in terms:
            qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))
    else:
        # Public view: block last-name enumeration
        if len(terms) == 1:
            # single token => treat as first name only
            first = terms[0]
            qs = qs.filter(first_name__icontains=first)
        else:
            # "First L." pattern allowed; ignore full surnames
            first = terms[0]
            last_token = terms[-1].rstrip('.')
            if len(last_token) == 1:
                qs = qs.filter(first_name__icontains=first, last_name__istartswith=last_token)
            else:
                # if they typed a full surname, fall back to first-name search only
                qs = qs.filter(first_name__icontains=first)

    results = list(qs[:25])  # small cap to avoid enumeration

    if len(results) == 1:
        return player_history(request, results[0].id)

    # names will be trimmed for anonymous via full_name(authenticated=…)
    return render(
        request,
        'ladder/player/results.html',
        {'players': results, 'query': escape(query)}
    )


def player_search(request):
    q = (request.GET.get('query') or '').strip()
    if len(q) < 2:
        return JsonResponse({"options": []})

    qs = Player.objects.all()
    for term in q.split():
        qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))

    authed = request.user.is_authenticated
    options = [{"id": p.id, "label": p.full_name(authenticated=authed)} for p in qs[:10]]
    return JsonResponse({"options": options})


def h2h_search(request, player_id):
    q = (request.GET.get('query') or '').strip()
    if not q:
        raise Http404

    terms = q.split()

    # Start with this player's results
    qs = Result.objects.filter(player_id=player_id)

    if request.user.is_authenticated:
        # Allow first OR last name searches
        for term in terms:
            qs = qs.filter(
                Q(opponent__first_name__icontains=term) |
                Q(opponent__last_name__icontains=term)
            )
    else:
        # Public: block last-name enumeration
        if len(terms) == 1:
            qs = qs.filter(opponent__first_name__icontains=terms[0])
        else:
            first = terms[0]
            last_token = terms[-1].rstrip('.')
            if len(last_token) == 1:  # allow "First L." pattern
                qs = qs.filter(
                    opponent__first_name__icontains=first,
                    opponent__last_name__istartswith=last_token
                )
            else:
                qs = qs.filter(opponent__first_name__icontains=first)

    # Aggregate and order by frequency
    head = (qs.values('opponent', 'opponent__first_name', 'opponent__last_name')
              .annotate(times_played=Count('opponent'))
              .order_by('-times_played')[:10])

    authed = request.user.is_authenticated

    # Build response: { opponent_id: "N x First Last/LastInitial." }
    def masked_name(first, last, authenticated):
        if not last:
            return first
        if authenticated:
            return f"{first} {last}"
        parts = last.split()
        parts[-1] = parts[-1][:1].capitalize() + '.'
        return f"{first} {' '.join(parts)}"

    results = {}
    for row in head:
        label = f"{row['times_played']} x " + masked_name(
            row['opponent__first_name'].strip(),
            row['opponent__last_name'].strip() if row['opponent__last_name'] else '',
            authed
        )
        results[row['opponent']] = escape(label)

    return HttpResponse(json.dumps({"options": results}), content_type="application/json")


def season_ajax_stats(request):

    season_id = request.GET.get('id', False)
    if season_id is False:
        raise Http404

    try:
        season_object = Season.objects.get(pk=season_id)
    except Season.DoesNotExist:
        raise Http404
    except ValueError:
        raise Http404

    stats = season_object.get_stats()

    include_leader = request.GET.get('leader', False)
    if include_leader:
        stats.update(season_object.get_leader_stats(user=request.user))

    return HttpResponse(json.dumps(stats), content_type="application/json")


def season_ajax_progress(request):
    season_id = request.GET.get('id', False)
    if season_id is False:
        raise Http404

    try:
        season_object = Season.objects.get(pk=season_id)
    except Season.DoesNotExist:
        raise Http404
    except ValueError:
        raise Http404

    return HttpResponse(json.dumps(season_object.get_progress()), content_type="application/json")

# views.py
# views.py  (replace the body of result_entry with this improved part)

@login_required
def result_entry(request):
    user = request.user
    try:
        ladder = (Ladder.objects
                  .filter(league__player__user=user, season__is_draft=False)
                  .order_by('-id')[0])
    except IndexError:
        raise Http404

    me = Player.objects.get(user=user)

    # Unplayed (kept as before)
    unplayed = _unplayed_opponents_for(me, ladder)

    # Entered: only matches where the logged-in player took part
    entered_raw = (
        Result.objects
        .filter(ladder=ladder)
        .filter(Q(player=me) | Q(opponent=me))  # <-- change models.Q -> Q
        .select_related('player', 'opponent', 'entered_by')
        .order_by('-date_added')
    )

    # Collapse mirror rows to a single “match”
    pairs = {}
    for r in entered_raw:
        key = tuple(sorted((r.player_id, r.opponent_id)))
        pairs.setdefault(key, []).append(r)

    entered = []
    for (a_id, b_id), rows in pairs.items():
        if len(rows) == 1:
            r = rows[0]
            # find mirror so we can compute losing score reliably
            try:
                mirror = Result.objects.get(ladder=ladder, player_id=r.opponent_id, opponent_id=r.player_id)
                rows = [r, mirror]
            except Result.DoesNotExist:
                continue

        # normalize winner/loser
        ra, rb = rows[0], rows[1]
        if ra.result == 9:
            winner_row, loser_row = ra, rb
        elif rb.result == 9:
            winner_row, loser_row = rb, ra
        else:
            # invalid pair (shouldn’t happen), skip
            continue

        entered.append({
            'winner': winner_row.player,
            'loser': loser_row.player,
            'losing_score': loser_row.result,
            'date_added': winner_row.date_added,     # use winner row date
            'entered_by': winner_row.entered_by or loser_row.entered_by,
            'pair_key': f'{a_id}-{b_id}',
        })

    # form as before
    result = Result(ladder=ladder, date_added=datetime.datetime.now(), result=0)
    form = AddEntryForm(ladder, user, instance=result)
    if unplayed:
        form.fields['opponent'].queryset = Player.objects.filter(id__in=[p.id for p in unplayed])
    else:
        form.fields['opponent'].queryset = Player.objects.none()

    return render(request, 'ladder/result/entry.html', {
        'user': user,
        'ladder': ladder,
        'form': form,
        'unplayed': unplayed,
        'entered': entered,
        'is_closed': ladder.is_closed(),
    })

# views.py
@login_required
def result_entry_add(request):
    user = request.user
    ladder = (Ladder.objects
              .filter(league__player__user=user, season__is_draft=False)
              .order_by('-id')[0])

    result = Result(ladder=ladder, date_added=datetime.datetime.now(), inaccurate_flag=0)
    form = AddEntryForm(ladder, user, request.POST, instance=result)

    if not form.is_valid():
        return render(request, 'ladder/result/entry.html', {
            'user': user, 'ladder': ladder, 'form': form,
            'unplayed': _unplayed_opponents_for(Player.objects.get(user=user), ladder),
            'entered': [],  # keep it simple on error; can repopulate if you prefer
        })

    user_result = form.save(commit=False)
    is_user_winner = form.cleaned_data['winner'] == 1
    losing_result = form.cleaned_data['result']
    me = user_result.player
    opp = user_result.opponent

    # de-duplicate if the pair already exists
    Result.objects.filter(ladder=ladder, player=me, opponent=opp).delete()
    Result.objects.filter(ladder=ladder, player=opp, opponent=me).delete()

    # build mirror
    opponent_result = Result(
        ladder=user_result.ladder,
        player=opp, opponent=me,
        result=9, date_added=user_result.date_added,
        inaccurate_flag=user_result.inaccurate_flag
    )

    if is_user_winner:
        opponent_result.result = losing_result
        user_result.result = 9
    else:
        # user lost; their result already is losing_result
        pass

    # log who entered
    user_result.entered_by = user
    opponent_result.entered_by = user

    user_result.save()
    opponent_result.save()

    return HttpResponseRedirect(reverse('result_entry'))

def _can_edit(user, ladder, player_a_id, player_b_id):
    if user.is_superuser:
        return True
    try:
        me = Player.objects.get(user=user)
    except Player.DoesNotExist:
        return False
    return me.id in (player_a_id, player_b_id)

@login_required
def result_entry_edit(request, pair_key):
    # pair_key format "<idA>-<idB>" sorted asc when created
    try:
        a_id, b_id = map(int, pair_key.split('-'))
    except ValueError:
        raise Http404

    ladder = (Ladder.objects
              .filter(league__player__user=request.user, season__is_draft=False)
              .order_by('-id')[0])

    if not _can_edit(request.user, ladder, a_id, b_id):
        return HttpResponseForbidden()

    # fetch the two rows
    try:
        r_ab = Result.objects.get(ladder=ladder, player_id=a_id, opponent_id=b_id)
        r_ba = Result.objects.get(ladder=ladder, player_id=b_id, opponent_id=a_id)
    except Result.DoesNotExist:
        raise Http404

    # normalize to winner/loser
    if r_ab.result == 9:
        winner, loser, losing_score = r_ab.player, r_ba.player, r_ba.result
    else:
        winner, loser, losing_score = r_ba.player, r_ab.player, r_ab.result

    if request.method == 'POST':
        # light friction: require a checkbox confirm and the new losing score
        confirmed = request.POST.get('confirm') == 'on'
        if not confirmed:
            messages.error(request, 'Please confirm you want to update this result.')
        else:
            new_winner_id = int(request.POST['winner_id'])
            new_losing_score = int(request.POST['losing_score'])
            if new_winner_id == winner.id and new_losing_score == losing_score:
                messages.info(request, 'No changes made.')
                return HttpResponseRedirect(reverse('result_entry'))

            # rewrite both rows
            win_id, lose_id = (a_id, b_id) if new_winner_id == a_id else (b_id, a_id)
            Result.objects.filter(ladder=ladder, player_id=a_id, opponent_id=b_id).delete()
            Result.objects.filter(ladder=ladder, player_id=b_id, opponent_id=a_id).delete()

            win_row = Result(ladder=ladder, player_id=win_id, opponent_id=lose_id, inaccurate_flag=0,
                             result=9, date_added=datetime.datetime.now(), entered_by=request.user)
            lose_row = Result(ladder=ladder, player_id=lose_id, opponent_id=win_id, inaccurate_flag=0,
                              result=new_losing_score, date_added=win_row.date_added, entered_by=request.user)
            win_row.save(); lose_row.save()
            messages.success(request, 'Result updated.')
            return HttpResponseRedirect(reverse('result_entry'))

    return render(request, 'ladder/result/edit.html', {
        'ladder': ladder,
        'pair_key': pair_key,
        'winner': winner, 'loser': loser, 'losing_score': losing_score
    })

@login_required
def result_entry_delete(request, pair_key):
    a_id, b_id = map(int, pair_key.split('-'))
    ladder = (Ladder.objects
              .filter(league__player__user=request.user, season__is_draft=False)
              .order_by('-id')[0])
    if not _can_edit(request.user, ladder, a_id, b_id):
        return HttpResponseForbidden()
    if request.method == 'POST':
        Result.objects.filter(ladder=ladder, player_id=a_id, opponent_id=b_id).delete()
        Result.objects.filter(ladder=ladder, player_id=b_id, opponent_id=a_id).delete()
        messages.success(request, 'Result removed.')
        return HttpResponseRedirect(reverse('result_entry'))
    return render(request, 'ladder/result/delete_confirm.html', {'pair_key': pair_key, 'ladder': ladder})

@csrf_exempt
def unsubscribe_token(request, token):
    """Supports human GET and machine POST (RFC 8058 one-click)."""
    subscription = get_object_or_404(LadderSubscription, unsubscribe_token=token)
    ladder = subscription.ladder
    year = ladder.season.start_date.year
    season_round = ladder.season.season_round
    division_id = ladder.division

    if request.method == "POST":
        # Gmail will send: Content-Type: application/x-www-form-urlencoded
        # body: "List-Unsubscribe=One-Click"
        if b"List-Unsubscribe=One-Click" in request.body:
            subscription.delete()
            return HttpResponse("Unsubscribed")  # plain 200 OK, no redirect
        return HttpResponseBadRequest("Malformed one-click request")

    # Human GET flow
    subscription.delete()
    messages.success(request, f"Successfully unsubscribed from {ladder} email notifications.")
    return HttpResponseRedirect(reverse("ladder", args=(year, season_round, division_id)))

