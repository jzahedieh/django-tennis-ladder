import datetime
import json

from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import send_mail
from django.db.models import Count
from django.http import HttpResponseRedirect, Http404, HttpResponse, HttpResponseForbidden, JsonResponse, \
    HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from ladder.forms import AddResultForm, AddEntryForm, EmailChangeForm
from ladder.models import Ladder, League, Player, Result, Season, LadderSubscription
from ladder.services.grid import LadderGridService
from ladder.services.player import PlayerStatsService
from ladder.services.result_entry import ResultMutationService, ResultNotFoundError
from ladder.services.stats import ClubStatsService

def index(request):
    current_season = Season.objects.filter(is_draft=False).latest('start_date')

    season_stats = current_season.get_stats()
    leader_stats = current_season.get_leader_stats(user=request.user)
    current_leaders = list(leader_stats.get('current_leaders', {}).values())
    progress_data = current_season.get_progress()
    recent_results = current_season.get_recent_results(user=request.user, limit=50)
    results_page_size = len(current_leaders) if len(current_leaders) >= 10 else 15

    context = {
        'current_season': current_season,
        'season_stats': season_stats,
        'current_leaders': current_leaders,
        'progress_data': progress_data,
        'progress_json': json.dumps(progress_data),
        'recent_results': recent_results,
        'results_page_size': results_page_size,
    }
    return render(request, 'ladder/index.html', context)


def stats(request):
    period = request.GET.get('period', 'all')
    year = request.GET.get('year')
    season_id = request.GET.get('season')

    context = ClubStatsService.get_club_stats(
        period=period,
        year=year,
        season_id=season_id,
        authenticated=request.user.is_authenticated,
    )
    return render(request, 'ladder/stats/index.html', context)


def list_rounds(request):
    seasons = list(
        Season.objects.filter(is_draft=False).order_by('-start_date', '-season_round')
    )
    season_ids = [s.id for s in seasons]

    divisions_by_season = {}
    players_by_season = {}
    total_matches_by_season = {}
    played_by_season = {}

    if season_ids:
        ladder_rows = (
            Ladder.objects.filter(season_id__in=season_ids)
            .annotate(league_count=Count('league'))
            .values('season_id', 'league_count')
        )
        for row in ladder_rows:
            sid = row['season_id']
            lc = int(row['league_count'] or 0)
            divisions_by_season[sid] = divisions_by_season.get(sid, 0) + 1
            players_by_season[sid] = players_by_season.get(sid, 0) + lc
            total_matches_by_season[sid] = total_matches_by_season.get(sid, 0) + (lc * (lc - 1) // 2)

        result_rows = (
            Result.objects.filter(ladder__season_id__in=season_ids)
            .values('ladder__season_id')
            .annotate(result_count=Count('id'))
        )
        played_by_season = {
            row['ladder__season_id']: int(row['result_count'] or 0) // 2
            for row in result_rows
        }

    total_divisions = 0
    total_matches_played = 0
    total_matches_scheduled = 0

    for idx, s in enumerate(seasons):
        divs = divisions_by_season.get(s.id, 0)
        players = players_by_season.get(s.id, 0)
        total_games = total_matches_by_season.get(s.id, 0)
        played = played_by_season.get(s.id, 0)
        pct = (played / total_games * 100.0) if total_games > 0 else 0.0

        s.divisions_count = divs
        s.player_count = players
        s.total_matches = total_games
        s.total_games_count = total_games
        s.matches_played = played
        s.results_count = played
        s.completion_pct = round(pct, 1)
        s.percentage_played = f"{pct:.2f}"
        s.is_latest = (idx == 0)

        total_divisions += divs
        total_matches_played += played
        total_matches_scheduled += total_games

    overall_pct = (
        (total_matches_played / total_matches_scheduled * 100.0)
        if total_matches_scheduled > 0
        else 0.0
    )
    years_span = (
        f"{seasons[-1].start_date.year}–{seasons[0].start_date.year}"
        if seasons
        else ""
    )
    available_years = sorted({s.start_date.year for s in seasons}, reverse=True)

    context = {
        'seasons': seasons,
        'available_years': available_years,
        'summary': {
            'total_seasons': len(seasons),
            'total_divisions': total_divisions,
            'total_matches_played': total_matches_played,
            'total_matches_scheduled': total_matches_scheduled,
            'overall_completion': f"{overall_pct:.1f}%",
            'years_span': years_span,
        },
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

    # Optimize with select_related / prefetch_related to avoid N+1 queries
    ladders = (
        Ladder.objects.filter(season=season_object)
        .select_related('season')
        .prefetch_related('league_set__player__user')
    )
    results = Result.objects.filter(ladder__season=season_object)
    ladders = LadderGridService.build_season_grids(
        season=season_object,
        ladders=ladders,
        results=results,
        user=request.user,
    )

    return render(
        request, 'ladder/season/index.html',
        {'season': season_object, 'ladders': ladders}
    )


def ladder(request, year, season_round, division_id):
    ladder_object = get_object_or_404(
        Ladder.objects.filter(season__is_draft=False)
        .select_related('season')
        .prefetch_related('league_set__player__user'),
        division=division_id,
        season__start_date__year=year,
        season__season_round=season_round
    )

    subscribed = False
    if request.user.is_authenticated:
        subscribed = LadderSubscription.objects.filter(
            user=request.user,
            ladder__division=division_id,
            ladder__season__start_date__year=year,
            ladder__season__season_round=season_round
        ).exists()  # Use exists() instead of count() > 0

    results = Result.objects.filter(ladder=ladder_object)
    grid = LadderGridService.build_ladder_grid(
        ladder=ladder_object,
        user=request.user,
        results=results,
    )

    recent_results = ladder_object.get_recent_results(user=request.user, limit=100)
    division_stats = ladder_object.get_stats(user=request.user, recent_results=recent_results)
    results_page_size = 6

    return render(request, 'ladder/ladder/index.html', {
        'ladder': ladder_object,
        'grid': grid,
        'subscribed': subscribed,
        'division_stats': division_stats,
        'recent_results': recent_results,
        'results_page_size': results_page_size,
    })

@login_required
@never_cache
def ladder_subscription(request, year, season_round, division_id):

    if not request.user.is_authenticated:
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
        Ladder.objects.select_related('season').prefetch_related('league_set__player__user'),
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


    # process or generate the score adding form
    if request.POST:
        form = AddResultForm(ladder_object, request.POST, instance=result)
        if form.is_valid():
            losing_result = form.save(commit=False)
            ResultMutationService.admin_submit_result(
                user=request.user,
                ladder=ladder_object,
                winner_id=losing_result.opponent_id,
                loser_id=losing_result.player_id,
                losing_score=losing_result.result,
                incomplete_reason=losing_result.incomplete_reason,
            )

            return HttpResponseRedirect(reverse('add', args=(
                ladder_object.season.start_date.year, ladder_object.season.season_round, ladder_object.division)))
    else:
        form = AddResultForm(ladder_object, instance=result)

    # prepare the results for displaying
    grid = LadderGridService.build_ladder_grid(
        ladder=ladder_object,
        user=request.user,
    )

    return render(request, 'ladder/ladder/add.html', {
        'ladder': ladder_object,
        'grid': grid,
        'form': form,
        'next_ladder': next_ladder,
        'previous_ladder': previous_ladder,
    })


def player_history(request, player_id):
    get_object_or_404(Player, pk=player_id)
    player = Player.objects.prefetch_related('result_player').get(pk=player_id)

    context = PlayerStatsService.get_player_profile(
        player=player,
        authenticated=request.user.is_authenticated,
    )
    context['centile_chart_json'] = json.dumps(context['centile_chart_data'])

    return render(request, 'ladder/player/history.html', context)


def head_to_head(request, player_id, opponent_id):
    player = get_object_or_404(Player, pk=player_id)
    opponent = get_object_or_404(Player, pk=opponent_id)

    context = PlayerStatsService.get_head_to_head(
        player=player,
        opponent=opponent,
        authenticated=request.user.is_authenticated,
    )

    if request.GET.get('modal') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'ladder/head_to_head/_modal_content.html', context)

    return render(request, 'ladder/head_to_head/index.html', context)


def player_result(request):
    query = request.GET.get('player_name', '').strip()
    if not query:
        raise Http404

    results = PlayerStatsService.search_players(
        query=query,
        authenticated=request.user.is_authenticated,
        limit=25,
    )

    if len(results) == 1:
        return player_history(request, results[0].id)

    return render(
        request,
        'ladder/player/results.html',
        {'players': results, 'query': query}
    )


def player_search(request):
    q = (request.GET.get('query') or '').strip()
    if len(q) < 2:
        return JsonResponse({"options": []})

    options = PlayerStatsService.autocomplete_players(
        query=q,
        authenticated=request.user.is_authenticated,
        limit=10,
    )
    return JsonResponse({"options": options})


@login_required
def result_entry(request):
    user = request.user
    try:
        me, ladder = ResultMutationService.get_active_ladder_for_user(user)
    except ResultNotFoundError:
        raise Http404

    unplayed = ResultMutationService.get_unplayed_opponents(me, ladder)
    entered = ResultMutationService.get_entered_matches(me, ladder)

    result = Result(ladder=ladder, date_added=datetime.datetime.now(), result=0)
    form = AddEntryForm(ladder, user, instance=result)
    if unplayed:
        form.fields['opponent'].queryset = Player.objects.filter(id__in=[p.id for p in unplayed])
    else:
        form.fields['opponent'].queryset = Player.objects.none()

    return render(request, 'ladder/result/entry.html', {
        'user': user,
        'me': me,
        'ladder': ladder,
        'form': form,
        'unplayed': unplayed,
        'entered': entered,
        'total_opponents': len(unplayed) + len(entered),
        'is_closed': ladder.is_closed(),
    })


@login_required
def result_entry_add(request):
    user = request.user
    try:
        me, ladder = ResultMutationService.get_active_ladder_for_user(user)
    except ResultNotFoundError:
        raise Http404

    result = Result(ladder=ladder, date_added=datetime.datetime.now())
    form = AddEntryForm(ladder, user, request.POST, instance=result)

    if not form.is_valid():
        unplayed = ResultMutationService.get_unplayed_opponents(me, ladder)
        entered = ResultMutationService.get_entered_matches(me, ladder)
        return render(request, 'ladder/result/entry.html', {
            'user': user,
            'me': me,
            'ladder': ladder,
            'form': form,
            'unplayed': unplayed,
            'entered': entered,
            'total_opponents': len(unplayed) + len(entered),
            'is_closed': ladder.is_closed(),
        })

    outcome = form.cleaned_data.get('outcome') or ('won' if form.cleaned_data.get('winner') else 'lost')
    primary_score = form.cleaned_data['result']
    opp = form.cleaned_data['opponent']

    ResultMutationService.submit_result(
        user=user,
        ladder=ladder,
        opponent_id=opp.id,
        outcome=outcome,
        primary_score=primary_score,
        opponent_score=form.cleaned_data.get('opponent_result'),
        incomplete_reason=form.cleaned_data.get('incomplete_reason'),
        injured_player=form.cleaned_data.get('injured_player'),
        enforce_open=False,
    )

    messages.success(request, 'Result added successfully')
    return HttpResponseRedirect(reverse('ladder', kwargs={
        'year': ladder.season.start_date.year,
        'season_round': ladder.season.season_round,
        'division_id': ladder.division,
    }))


@login_required
def result_entry_edit(request, pair_key):
    me = Player.objects.filter(user=request.user).first()
    try:
        info = ResultMutationService.get_match_pair(pair_key, viewer_player=me)
    except ResultNotFoundError:
        raise Http404

    ladder = info['ladder']
    a_id = info['a_id']
    b_id = info['b_id']

    if not ResultMutationService.can_edit_match(request.user, ladder, a_id, b_id):
        return HttpResponseForbidden()

    winner = info['winner']
    loser = info['loser']
    winner_score = info['winner_score']
    losing_score = info['losing_score']
    match_mode = info['match_mode']

    if request.method == 'POST':
        confirmed = request.POST.get('confirm') == 'on'
        if not confirmed:
            messages.error(request, 'Please confirm you want to update this result.')
        else:
            new_mode = request.POST.get('match_mode') or 'completed'
            if new_mode == 'time':
                score_w = max(0, min(8, int(request.POST.get('winner_score', winner_score if match_mode == 'time' else 4))))
                score_l = max(0, min(8, int(request.POST.get('losing_score', losing_score))))
                _, changed = ResultMutationService.edit_result(
                    user=request.user,
                    pair_key=pair_key,
                    match_mode='time',
                    winner_score=score_w,
                    losing_score=score_l,
                    enforce_open=False,
                )
            else:
                new_winner_id = int(request.POST['winner_id'])
                new_losing_score = max(0, min(8, int(request.POST['losing_score'])))
                _, changed = ResultMutationService.edit_result(
                    user=request.user,
                    pair_key=pair_key,
                    match_mode=new_mode,
                    winner_id=new_winner_id,
                    losing_score=new_losing_score,
                    enforce_open=False,
                )

            if not changed:
                messages.info(request, 'No changes made - result already matches')
            else:
                messages.success(request, 'Result updated')
            return HttpResponseRedirect(reverse('ladder', kwargs={
                'year': ladder.season.start_date.year,
                'season_round': ladder.season.season_round,
                'division_id': ladder.division,
            }))

    return render(request, 'ladder/result/edit.html', {
        'ladder': ladder,
        'pair_key': pair_key,
        'me': me,
        'winner': winner,
        'loser': loser,
        'winner_score': winner_score,
        'losing_score': losing_score,
        'match_mode': match_mode,
    })


@login_required
def result_entry_delete(request, pair_key):
    try:
        info = ResultMutationService.get_match_pair(pair_key)
    except ResultNotFoundError:
        raise Http404

    ladder = info['ladder']
    if not ResultMutationService.can_edit_match(request.user, ladder, info['a_id'], info['b_id']):
        return HttpResponseForbidden()

    if request.method == 'POST':
        ResultMutationService.delete_result(
            user=request.user, pair_key=pair_key, enforce_open=False
        )
        messages.success(request, 'Result removed')
        return HttpResponseRedirect(reverse('ladder', kwargs={
            'year': ladder.season.start_date.year,
            'season_round': ladder.season.season_round,
            'division_id': ladder.division,
        }))

    return render(request, 'ladder/result/delete_confirm.html', {
        'pair_key': pair_key,
        'ladder': ladder,
        'winner': info['winner'],
        'loser': info['loser'],
        'winner_score': info['winner_score'],
        'losing_score': info['losing_score'],
        'is_incomplete': info['is_incomplete'],
        'is_injury': info['is_injury'],
    })

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


@login_required
def account(request):
    user = request.user
    player = Player.objects.filter(user=user).first()

    current_season = Season.objects.filter(is_draft=False).order_by('-start_date').first()
    current_league = None
    latest_league = None

    if player:
        if current_season:
            current_league = (
                League.objects
                .filter(player=player, ladder__season=current_season)
                .select_related('ladder__season')
                .first()
            )
        latest_league = (
            League.objects
            .filter(player=player, ladder__season__is_draft=False)
            .select_related('ladder__season')
            .order_by('-ladder__season__start_date', 'ladder__division')
            .first()
        )

    email_form = EmailChangeForm(user=user)
    password_form = PasswordChangeForm(user=user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_email' or ('email' in request.POST and 'old_password' not in request.POST):
            old_email = (user.email or user.username or '').strip()
            email_form = EmailChangeForm(user=user, data=request.POST)
            if email_form.is_valid():
                new_email = email_form.cleaned_data['email']
                email_changed = old_email.lower() != new_email.lower()
                email_form.save()
                if email_changed:
                    recipients = [addr for addr in dict.fromkeys([old_email, new_email]) if '@' in addr]
                    if recipients:
                        player_name = f"{player.first_name} {player.last_name}".strip() if player else (user.get_full_name() or new_email)
                        send_mail(
                            subject='Highgate Ladder - Email Address Updated',
                            message=(
                                f"Hi {player_name},\n\n"
                                f"The email address for your Highgate Ladder account has been changed from {old_email} to {new_email}.\n\n"
                                f"You can now use {new_email} to log in and receive division notifications.\n\n"
                                f"If you did not request this change, please contact feedback@highgate-ladder.co.uk."
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL or settings.SUBSCRIPTION_EMAIL,
                            recipient_list=recipients,
                            fail_silently=True,
                        )
                messages.success(request, 'Your email address has been updated successfully.')
                return HttpResponseRedirect(reverse('account'))
        else:
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                updated_user = password_form.save()
                update_session_auth_hash(request, updated_user)
                messages.success(request, 'Your password has been updated successfully.')
                return HttpResponseRedirect(reverse('account'))

    for form in (email_form, password_form):
        for name, field in form.fields.items():
            css_class = 'form-control'
            if form.is_bound and form[name].errors:
                css_class += ' is-invalid'
            field.widget.attrs['class'] = css_class
            field.widget.attrs.pop('autofocus', None)

    return render(request, 'ladder/account/index.html', {
        'player': player,
        'current_season': current_season,
        'current_league': current_league,
        'latest_league': latest_league,
        'email_form': email_form,
        'password_form': password_form,
    })


