import datetime

from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Router

from api.auth import JWTAuth, OptionalJWTAuth, is_authenticated_request
from api.schemas.auth import ActiveDivisionRef
from api.schemas.ladder import (
    AdminSubmitResultIn,
    ClubStatsOut,
    CurrentSeasonOverviewOut,
    DivisionDetailOut,
    EditResultIn,
    ResultEntryContextOut,
    ResultMutationOut,
    SeasonDetailOut,
    SeasonListOut,
    SubmitResultIn,
    SubscriptionToggleOut,
)
from api.serializers import (
    build_active_division_ref,
    serialize_division_grid,
    serialize_division_stats,
    serialize_recent_match,
    serialize_season_summary,
)
from ladder.models import Ladder, LadderSubscription, League, Player, Result, Season
from ladder.services.grid import LadderGridService
from ladder.services.result_entry import (
    ResultMutationError,
    ResultMutationService,
    ResultNotFoundError,
)
from ladder.services.stats import ClubStatsService

router = Router()


def _build_my_division_summary(user, current_season: Season) -> dict | None:
    player = Player.objects.filter(user=user).first()
    if player is None:
        return None

    league = (
        League.objects.filter(player=player, ladder__season=current_season)
        .select_related("ladder__season")
        .order_by("ladder__division")
        .first()
    )
    if league is None:
        return None

    ladder = (
        Ladder.objects.filter(pk=league.ladder_id)
        .select_related("season")
        .prefetch_related("league_set__player__user")
        .first()
    )
    grid = LadderGridService.build_ladder_grid(ladder=ladder, user=user)
    rows = grid["rows"]
    ranked_rows = sorted(
        rows, key=lambda r: (-int(r["total"]), r["position"])
    )

    my_row = None
    rank_in_division = 1
    for idx, row in enumerate(ranked_rows, start=1):
        if row["player_id"] == player.id:
            my_row = row
            rank_in_division = idx
            break

    division_size = len(rows)
    return {
        "ladder_id": ladder.id,
        "division": ladder.division,
        "matches_played": int(my_row["matches_played"]) if my_row else 0,
        "total_opponents": max(0, division_size - 1),
        "total_points": int(my_row["total"]) if my_row else 0,
        "rank_in_division": rank_in_division,
        "division_size": division_size,
        "is_closed": ladder.is_closed(),
    }


@router.get(
    "/seasons/current/overview",
    response=CurrentSeasonOverviewOut,
    auth=OptionalJWTAuth(),
)
def current_season_overview(request):
    current_season = (
        Season.objects.filter(is_draft=False)
        .order_by("-start_date", "-season_round")
        .first()
    )
    if current_season is None:
        raise Http404("No published seasons found.")

    authenticated = is_authenticated_request(request)
    user = request.auth

    raw_stats = current_season.get_stats()
    leader_stats = current_season.get_leader_stats(user=user)
    leaders = [
        {
            "division": item["division"],
            "player": item["player"],
            "player_id": item["player_id"],
            "total": item["total"],
            "played": float(item["played"]),
        }
        for item in leader_stats.get("current_leaders", {}).values()
    ]
    progress = current_season.get_progress()
    recent_raw = current_season.get_recent_results(user=user, limit=50)
    year = current_season.start_date.year
    s_round = current_season.season_round

    return {
        "season": serialize_season_summary(current_season),
        "stats": {
            "divisions": int(raw_stats["divisions"]),
            "percentage_played": str(raw_stats["percentage_played"]),
            "total_games_count": int(round(raw_stats["total_games_count"])),
            "results_count": int(round(raw_stats["results_count"])),
            "player_count": int(raw_stats["player_count"]),
        },
        "leaders": leaders,
        "progress": progress,
        "recent_results": [
            serialize_recent_match(m, year=year, season_round=s_round)
            for m in recent_raw
        ],
        "my_division": _build_my_division_summary(user, current_season)
        if authenticated
        else None,
    }


@router.get("/seasons/", response=SeasonListOut, auth=OptionalJWTAuth())
def list_seasons(request):
    seasons = list(
        Season.objects.filter(is_draft=False).order_by("-start_date", "-season_round")
    )
    season_ids = [s.id for s in seasons]

    divisions_by_season = {}
    players_by_season = {}
    total_matches_by_season = {}
    played_by_season = {}

    if season_ids:
        ladder_rows = (
            Ladder.objects.filter(season_id__in=season_ids)
            .annotate(league_count=Count("league"))
            .values("season_id", "league_count")
        )
        for row in ladder_rows:
            sid = row["season_id"]
            lc = int(row["league_count"] or 0)
            divisions_by_season[sid] = divisions_by_season.get(sid, 0) + 1
            players_by_season[sid] = players_by_season.get(sid, 0) + lc
            total_matches_by_season[sid] = (
                total_matches_by_season.get(sid, 0) + (lc * (lc - 1) // 2)
            )

        result_rows = (
            Result.objects.filter(ladder__season_id__in=season_ids)
            .values("ladder__season_id")
            .annotate(result_count=Count("id"))
        )
        played_by_season = {
            row["ladder__season_id"]: int(row["result_count"] or 0) // 2
            for row in result_rows
        }

    total_divisions = 0
    total_matches_played = 0
    total_matches_scheduled = 0
    season_items = []

    for idx, s in enumerate(seasons):
        divs = divisions_by_season.get(s.id, 0)
        players = players_by_season.get(s.id, 0)
        total_games = total_matches_by_season.get(s.id, 0)
        played = played_by_season.get(s.id, 0)
        pct = (played / total_games * 100.0) if total_games > 0 else 0.0

        total_divisions += divs
        total_matches_played += played
        total_matches_scheduled += total_games

        season_items.append(
            {
                "id": s.id,
                "name": s.name,
                "year": s.start_date.year,
                "season_round": s.season_round,
                "start_date": s.start_date,
                "end_date": s.end_date,
                "divisions_count": divs,
                "player_count": players,
                "total_matches": total_games,
                "matches_played": played,
                "completion_pct": round(pct, 1),
                "is_latest": idx == 0,
            }
        )

    overall_pct = (
        (total_matches_played / total_matches_scheduled * 100.0)
        if total_matches_scheduled > 0
        else 0.0
    )
    years_span = (
        f"{seasons[-1].start_date.year}\u2013{seasons[0].start_date.year}"
        if seasons
        else ""
    )
    available_years = sorted({s.start_date.year for s in seasons}, reverse=True)

    return {
        "seasons": season_items,
        "available_years": available_years,
        "summary": {
            "total_seasons": len(seasons),
            "total_divisions": total_divisions,
            "total_matches_played": total_matches_played,
            "total_matches_scheduled": total_matches_scheduled,
            "overall_completion": f"{overall_pct:.1f}%",
            "years_span": years_span,
        },
    }


@router.get(
    "/seasons/{year}/round/{season_round}/",
    response=SeasonDetailOut,
    auth=OptionalJWTAuth(),
)
def season_detail(request, year: int, season_round: int):
    season_obj = get_object_or_404(
        Season, start_date__year=year, season_round=season_round
    )
    if season_obj.is_draft and not getattr(request.auth, "is_superuser", False):
        raise Http404("Season not found.")

    ladders = (
        Ladder.objects.filter(season=season_obj)
        .order_by("division")
        .select_related("season")
        .prefetch_related("league_set__player__user")
    )
    results = Result.objects.filter(ladder__season=season_obj)
    ladders = LadderGridService.build_season_grids(
        season=season_obj,
        ladders=ladders,
        results=results,
        user=request.auth,
    )

    return {
        "season": serialize_season_summary(season_obj),
        "divisions": [serialize_division_grid(ld) for ld in ladders],
    }


@router.get(
    "/seasons/{year}/round/{season_round}/division/{division_id}/",
    response=DivisionDetailOut,
    auth=OptionalJWTAuth(),
)
def division_detail(request, year: int, season_round: int, division_id: int):
    qs = (
        Ladder.objects.select_related("season")
        .prefetch_related("league_set__player__user")
    )
    if not getattr(request.auth, "is_superuser", False):
        qs = qs.filter(season__is_draft=False)

    ladder_obj = get_object_or_404(
        qs,
        division=division_id,
        season__start_date__year=year,
        season__season_round=season_round,
    )

    authenticated = is_authenticated_request(request)
    subscribed = False
    if authenticated:
        subscribed = LadderSubscription.objects.filter(
            user=request.auth, ladder=ladder_obj
        ).exists()

    results = Result.objects.filter(ladder=ladder_obj)
    LadderGridService.build_ladder_grid(
        ladder=ladder_obj,
        user=request.auth,
        results=results,
    )

    recent_results = ladder_obj.get_recent_results(user=request.auth, limit=100)
    division_stats = ladder_obj.get_stats(
        user=request.auth, recent_results=recent_results
    )

    sibling_divisions = set(
        Ladder.objects.filter(
            season=ladder_obj.season,
            division__in=(division_id - 1, division_id + 1),
        ).values_list("division", flat=True)
    )

    return {
        "season": serialize_season_summary(ladder_obj.season),
        "ladder_id": ladder_obj.id,
        "division": ladder_obj.division,
        "ladder_type": ladder_obj.ladder_type,
        "is_closed": ladder_obj.is_closed(),
        "subscribed": subscribed,
        "can_admin_enter": bool(getattr(request.auth, "is_superuser", False)),
        "has_prev_division": (division_id - 1) in sibling_divisions,
        "has_next_division": (division_id + 1) in sibling_divisions,
        "grid": serialize_division_grid(ladder_obj),
        "stats": serialize_division_stats(division_stats),
        "recent_results": [
            serialize_recent_match(m, year=year, season_round=season_round)
            for m in recent_results
        ],
    }


@router.post(
    "/seasons/{year}/round/{season_round}/division/{division_id}/subscription/",
    response=SubscriptionToggleOut,
    auth=JWTAuth(),
)
def toggle_division_subscription(
    request, year: int, season_round: int, division_id: int
):
    ladder_obj = get_object_or_404(
        Ladder,
        division=division_id,
        season__start_date__year=year,
        season__season_round=season_round,
        season__is_draft=False,
    )
    existing = LadderSubscription.objects.filter(
        user=request.auth, ladder=ladder_obj
    )
    if existing.exists():
        existing.delete()
        return {
            "subscribed": False,
            "detail": "Unsubscribed from email notifications.",
        }

    LadderSubscription.objects.create(
        user=request.auth,
        ladder=ladder_obj,
        subscribed_at=datetime.date.today(),
    )
    return {
        "subscribed": True,
        "detail": "Subscribed to email notifications.",
    }


def _opponent_h2h_map(me: Player, opponent_ids: list[int]) -> dict[int, tuple[int, int, int]]:
    if not opponent_ids:
        return {}

    rows = Result.objects.filter(
        player=me,
        opponent_id__in=opponent_ids,
        ladder__season__is_draft=False,
    ).values_list("opponent_id", "result", "incomplete_reason")

    summary = {oid: [0, 0, 0] for oid in opponent_ids}
    for opp_id, score, reason in rows:
        bucket = summary[opp_id]
        bucket[0] += 1
        if reason != Result.IncompleteReason.TIME:
            if score == 9:
                bucket[1] += 1
            else:
                bucket[2] += 1
    return {oid: (vals[0], vals[1], vals[2]) for oid, vals in summary.items()}


@router.get("/results/entry/", response=ResultEntryContextOut, auth=JWTAuth())
def result_entry_context(request):
    try:
        me, ladder = ResultMutationService.get_active_ladder_for_user(request.auth)
    except ResultNotFoundError:
        player = Player.objects.filter(user=request.auth).first()
        return {
            "has_active_ladder": False,
            "ladder": None,
            "player_id": player.id if player else None,
            "player_name": player.full_name(authenticated=True) if player else None,
            "is_closed": False,
            "total_opponents": 0,
            "unplayed": [],
            "entered": [],
        }

    unplayed = ResultMutationService.get_unplayed_opponents(me, ladder)
    entered = ResultMutationService.get_entered_matches(me, ladder)
    h2h_map = _opponent_h2h_map(me, [p.id for p in unplayed])

    return {
        "has_active_ladder": True,
        "ladder": build_active_division_ref(ladder),
        "player_id": me.id,
        "player_name": me.full_name(authenticated=True),
        "is_closed": ladder.is_closed(),
        "total_opponents": len(unplayed) + len(entered),
        "unplayed": [
            {
                "id": opp.id,
                "name": opp.full_name(authenticated=True),
                "h2h_played": h2h_map.get(opp.id, (0, 0, 0))[0],
                "h2h_won": h2h_map.get(opp.id, (0, 0, 0))[1],
                "h2h_lost": h2h_map.get(opp.id, (0, 0, 0))[2],
            }
            for opp in unplayed
        ],
        "entered": [
            {
                "pair_key": item["pair_key"],
                "opponent_id": item["opponent"].id,
                "opponent_name": item["opponent"].full_name(authenticated=True),
                "winner_id": item["winner"].id,
                "loser_id": item["loser"].id,
                "my_score": int(item["my_score"]),
                "opp_score": int(item["opp_score"]),
                "losing_score": int(item["losing_score"]),
                "outcome_code": item["outcome_code"],
                "is_incomplete": bool(item["is_incomplete"]),
                "is_injury": bool(item["is_injury"]),
                "incomplete_reason": item["incomplete_reason"],
                "score_display": item["score_display"],
                "date_added": item["date_added"],
            }
            for item in entered
        ],
    }


@router.post("/results/entry/", response=ResultMutationOut, auth=JWTAuth())
def submit_result(request, payload: SubmitResultIn):
    _, ladder = ResultMutationService.get_active_ladder_for_user(request.auth)
    result = ResultMutationService.submit_result(
        user=request.auth,
        ladder=ladder,
        opponent_id=payload.opponent_id,
        outcome=payload.outcome,
        primary_score=payload.primary_score,
        opponent_score=payload.opponent_score,
        incomplete_reason=payload.incomplete_reason,
        injured_player=payload.injured_player,
        enforce_open=True,
    )
    return {
        "pair_key": result["pair_key"],
        "changed": True,
        "detail": "Result added successfully.",
    }


@router.put("/results/entry/{pair_key}/", response=ResultMutationOut, auth=JWTAuth())
def edit_result(request, pair_key: str, payload: EditResultIn):
    _, changed = ResultMutationService.edit_result(
        user=request.auth,
        pair_key=pair_key,
        match_mode=payload.match_mode,
        winner_id=payload.winner_id,
        winner_score=payload.winner_score,
        losing_score=payload.losing_score,
        enforce_open=True,
    )
    return {
        "pair_key": pair_key,
        "changed": changed,
        "detail": "Result updated." if changed else "No changes made - result already matches.",
    }


@router.delete("/results/entry/{pair_key}/", response=ResultMutationOut, auth=JWTAuth())
def delete_result(request, pair_key: str):
    ResultMutationService.delete_result(
        user=request.auth, pair_key=pair_key, enforce_open=True
    )
    return {
        "pair_key": pair_key,
        "changed": True,
        "detail": "Result removed.",
    }


@router.post(
    "/results/admin/{year}/round/{season_round}/division/{division_id}/",
    response=ResultMutationOut,
    auth=JWTAuth(),
)
def admin_submit_result(
    request,
    year: int,
    season_round: int,
    division_id: int,
    payload: AdminSubmitResultIn,
):
    ladder_obj = get_object_or_404(
        Ladder,
        division=division_id,
        season__start_date__year=year,
        season__season_round=season_round,
        season__is_draft=False,
    )
    result = ResultMutationService.admin_submit_result(
        user=request.auth,
        ladder=ladder_obj,
        winner_id=payload.winner_id,
        loser_id=payload.loser_id,
        losing_score=payload.losing_score,
        incomplete_reason=payload.incomplete_reason,
    )
    return {
        "pair_key": result["pair_key"],
        "changed": True,
        "detail": "Admin result saved.",
    }


@router.get("/stats/", response=ClubStatsOut, auth=OptionalJWTAuth())
def club_stats(
    request,
    period: str = "all",
    year: int | None = None,
    season_id: int | None = None,
):
    data = ClubStatsService.get_club_stats(
        period=period,
        year=year,
        season_id=season_id,
        authenticated=is_authenticated_request(request),
    )

    flt = data["filter"]
    return {
        "filter": {
            "filter_type": flt["filter_type"],
            "period": flt["period"],
            "selected_year": flt["selected_year"],
            "selected_season_id": flt["selected_season_id"],
            "filter_label": flt["filter_label"],
            "min_rounds": flt["min_rounds"],
        },
        "available_years": data["available_years"],
        "available_seasons": [
            {
                "id": s.id,
                "name": s.name,
                "year": s.start_date.year,
                "season_round": s.season_round,
            }
            for s in data["available_seasons"]
        ],
        "summary": data["summary"],
        "leaderboards": data["leaderboards"],
        "page_size": data["page_size"],
    }
