import datetime

from ladder.models import Ladder, League, Player, Season


def build_active_division_ref(ladder: Ladder) -> dict:
    return {
        "season_id": ladder.season_id,
        "season_name": str(ladder.season),
        "year": ladder.season.start_date.year,
        "season_round": ladder.season.season_round,
        "division": ladder.division,
        "ladder_id": ladder.id,
        "is_closed": ladder.is_closed(),
    }


def get_current_published_season() -> Season | None:
    return (
        Season.objects.filter(is_draft=False)
        .order_by("-start_date", "-season_round")
        .first()
    )


def get_current_division_for_player(player: Player | None) -> Ladder | None:
    if player is None:
        return None
    current_season = get_current_published_season()
    if current_season is None:
        return None
    league = (
        League.objects.filter(player=player, ladder__season=current_season)
        .select_related("ladder__season")
        .order_by("ladder__division")
        .first()
    )
    return league.ladder if league else None


def build_user_me(user) -> dict:
    player = Player.objects.filter(user=user).first()
    roles = sorted(user.groups.values_list("name", flat=True))
    if (user.is_staff or user.is_superuser) and "admin" not in roles:
        roles.append("admin")

    active_ladder = get_current_division_for_player(player)
    return {
        "id": user.id,
        "email": (user.email or user.username or "").strip(),
        "first_name": user.first_name or (player.first_name if player else ""),
        "last_name": user.last_name or (player.last_name if player else ""),
        "is_staff": bool(user.is_staff),
        "is_superuser": bool(user.is_superuser),
        "roles": roles,
        "player_id": player.id if player else None,
        "player_name": player.full_name(authenticated=True) if player else None,
        "active_division": build_active_division_ref(active_ladder)
        if active_ladder
        else None,
    }


def serialize_season_summary(season_obj: Season) -> dict:
    return {
        "id": season_obj.id,
        "name": season_obj.name,
        "year": season_obj.start_date.year,
        "season_round": season_obj.season_round,
        "start_date": season_obj.start_date,
        "end_date": season_obj.end_date,
        "is_draft": bool(season_obj.is_draft),
        "is_closed": datetime.date.today() > season_obj.end_date,
    }


def serialize_division_grid(ladder_obj: Ladder) -> dict:
    grid = ladder_obj.grid
    rows = []
    for row in grid["rows"]:
        cells = [
            {
                "is_self": bool(cell["is_self"]),
                "player_id": cell["player_id"],
                "opponent_id": cell["opponent_id"],
                "opponent_name": cell.get("opponent_name"),
                "result": cell.get("result"),
            }
            for cell in row["cells"]
        ]
        rows.append(
            {
                "position": row["position"],
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "is_current_user": bool(row["is_current_user"]),
                "cells": cells,
                "total": int(row["total"]),
                "average": row["average"],
                "matches_played": int(row["matches_played"]),
            }
        )
    return {
        "ladder_id": ladder_obj.id,
        "division": ladder_obj.division,
        "ladder_type": ladder_obj.ladder_type,
        "rows": rows,
    }


def serialize_recent_match(match: dict, year: int, season_round: int) -> dict:
    return {
        "winner_id": match["winner_id"],
        "winner_name": match["winner_name"],
        "loser_id": match["loser_id"],
        "loser_name": match["loser_name"],
        "winner_score": int(match["winner_score"]),
        "loser_score": int(match["loser_score"]),
        "score_display": match["score_display"],
        "is_incomplete": bool(match["is_incomplete"]),
        "is_injury": bool(match["is_injury"]),
        "incomplete_reason": match.get("incomplete_reason"),
        "division": int(match["division"]),
        "year": year,
        "season_round": season_round,
        "date_added": match["date_added"],
        "date_display": match["date_display"],
        "date_full": match["date_full"],
    }


def _serialize_division_leader_stat(item: dict | None) -> dict | None:
    if item is None:
        return None
    return {
        "player_id": item["player_id"],
        "player_name": item["player_name"],
        "total": int(item["total"]),
        "played": int(item["played"]),
        "won": int(item["won"]),
        "lost": int(item["lost"]),
        "retired": int(item["retired"]),
        "incomplete": int(item["incomplete"]),
        "avg": str(item["avg"]),
        "max_possible": int(item["max_possible"]),
    }


def serialize_division_stats(stats: dict) -> dict:
    return {
        "players_count": int(stats["players_count"]),
        "total_matches_played": int(stats["total_matches_played"]),
        "total_matches": int(stats["total_matches"]),
        "matches_remaining": int(stats["matches_remaining"]),
        "perc_matches_played": float(stats["perc_matches_played"]),
        "leader": _serialize_division_leader_stat(stats.get("leader")),
        "leaders": [
            _serialize_division_leader_stat(item)
            for item in stats.get("leaders", [])
        ],
        "avg_match_score": stats.get("avg_match_score"),
        "avg_games_per_match": stats.get("avg_games_per_match"),
        "total_games_played": int(stats.get("total_games_played", 0)),
        "close_matches_count": int(stats.get("close_matches_count", 0)),
        "close_matches_pct": float(stats.get("close_matches_pct", 0.0)),
    }


def serialize_h2h_summary(rec: dict | None) -> dict | None:
    if rec is None:
        return None
    return {
        "opponent_id": rec["opponent"],
        "opponent_name": rec["opponent_name"],
        "times_played": int(rec["times_played"]),
        "won": int(rec["won"]),
        "lost": int(rec["lost"]),
        "retired": int(rec["retired"]),
        "incomplete": int(rec["incomplete"]),
        "win_rate": float(rec["win_rate"]),
        "win_rate_display": rec["win_rate_display"],
        "won_played_display": rec["won_played_display"],
        "last_played": rec.get("last_played"),
    }
