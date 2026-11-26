from django.shortcuts import get_object_or_404
from ninja import Router

from api.auth import OptionalJWTAuth, is_authenticated_request
from api.schemas.players import (
    HeadToHeadOut,
    PlayerProfileOut,
    PlayerSearchOut,
)
from api.serializers import serialize_h2h_summary
from ladder.models import Player
from ladder.services.player import PlayerStatsService

router = Router(auth=OptionalJWTAuth())


@router.get("/search/", response=PlayerSearchOut)
def search_players(request, q: str = "", limit: int = 10):
    query = (q or "").strip()
    if len(query) < 2:
        return {"options": []}

    clamped_limit = max(1, min(limit, 25))
    options = PlayerStatsService.autocomplete_players(
        query=query,
        authenticated=is_authenticated_request(request),
        limit=clamped_limit,
    )
    return {"options": options}


@router.get("/{player_id}/", response=PlayerProfileOut)
def player_profile(request, player_id: int):
    player = get_object_or_404(
        Player.objects.prefetch_related("result_player"), pk=player_id
    )
    authenticated = is_authenticated_request(request)
    data = PlayerStatsService.get_player_profile(
        player=player, authenticated=authenticated
    )

    raw_stats = dict(data["player_stats"])
    raw_stats.setdefault("completion_rate", "- %")

    raw_insights = dict(data["insights"])
    raw_insights["most_played_rival"] = serialize_h2h_summary(
        raw_insights.get("most_played_rival")
    )
    raw_insights["favourite_rival"] = serialize_h2h_summary(
        raw_insights.get("favourite_rival")
    )
    raw_insights["toughest_rival"] = serialize_h2h_summary(
        raw_insights.get("toughest_rival")
    )

    season_history = []
    for lg in data["league_set"]:
        st = lg.computed_stats
        season_obj = lg.ladder.season
        season_history.append(
            {
                "league_id": lg.id,
                "season_id": season_obj.id,
                "season_name": str(season_obj),
                "year": season_obj.start_date.year,
                "season_round": season_obj.season_round,
                "division": lg.ladder.division,
                "total_points": float(st["total_points"]),
                "games": int(st["games"]),
                "scheduled_matches": int(lg.scheduled_matches),
                "points_per_game": round(float(st["pointsdivgames"]), 2),
                "won_count": int(st["won_count"]),
                "pct_played": round(float(st["percplayed"]), 1),
                "is_division_winner": bool(lg.is_division_winner),
                "centile": lg.centile,
                "rank": lg.centile_rank,
                "total_players": lg.centile_total,
            }
        )

    return {
        "player_id": player.id,
        "player_name": data["player_name"],
        "is_authenticated_view": authenticated,
        "stats": raw_stats,
        "insights": raw_insights,
        "centile_chart_data": data["centile_chart_data"],
        "head_to_head": [serialize_h2h_summary(h) for h in data["head"]],
        "season_history": season_history,
    }


@router.get("/{player_id}/vs/{opponent_id}/", response=HeadToHeadOut)
def head_to_head(request, player_id: int, opponent_id: int):
    player = get_object_or_404(Player, pk=player_id)
    opponent = get_object_or_404(Player, pk=opponent_id)
    authenticated = is_authenticated_request(request)

    data = PlayerStatsService.get_head_to_head(
        player=player, opponent=opponent, authenticated=authenticated
    )

    matches = [
        {
            "date_added": m["date_added"],
            "year": m["year"],
            "season_round": m["season_round"],
            "division": m["division"],
            "ladder_full": m["ladder_full"],
            "ladder_short": m["ladder_short"],
            "player_won": m["player_won"],
            "is_incomplete": m["is_incomplete"],
            "is_injury": m["is_injury"],
            "winner_badge": m["winner_badge"],
            "loser_badge": m["loser_badge"],
            "winner_id": m["winner_id"],
            "winner_name": m["winner_name"],
            "loser_id": m["loser_id"],
            "loser_name": m["loser_name"],
            "winner_score": m["winner_score"],
            "losing_score": m["losing_score"],
            "player_score": m["player_score"],
            "opponent_score": m["opponent_score"],
            "score_display": m["score_display"],
            "is_close": m["is_close"],
        }
        for m in data["matches"]
    ]

    return {
        "player_id": player.id,
        "player_name": data["player_name"],
        "opponent_id": opponent.id,
        "opponent_name": data["opponent_name"],
        "stats": data["stats"],
        "matches": matches,
    }
