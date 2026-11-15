from collections import defaultdict

from django.urls import reverse

from ladder.models import Ladder, Result


class LadderGridService:
    """
    Service for building cross-table division grids with pre-calculated
    head-to-head cells, total points, and scoring averages.
    """

    @staticmethod
    def calculate_points(score: int) -> int:
        """
        Return ladder points for a single match score:
        9 games + 3 bonus points for a win (12), or games + 1 point otherwise.
        """
        return score + 3 if score == 9 else score + 1

    @classmethod
    def calculate_totals_and_average(cls, results) -> tuple[int, str | int]:
        """
        Calculate total ladder points and formatted 2-decimal average for a
        collection of Result objects (or integer scores). Returns (0, 0) when unplayed.
        """
        total = 0
        count = 0
        for item in results:
            score = item.result if hasattr(item, "result") else item
            total += cls.calculate_points(score)
            count += 1

        average = f"{total / count:.2f}" if count > 0 else 0
        return total, average

    @classmethod
    def build_ladder_grid(cls, ladder: Ladder, user=None, results=None) -> dict:
        """
        Build the cross-table matrix and per-player scoring stats for a single division.
        Attaches the resulting view-model onto `ladder.grid` and returns it.
        """
        authenticated = bool(getattr(user, "is_authenticated", False))
        current_user_id = user.id if authenticated else None

        prefetched = getattr(ladder, "_prefetched_objects_cache", {})
        if "league_set" in prefetched:
            leagues = list(ladder.league_set.all())
        else:
            leagues = list(ladder.league_set.select_related("player", "player__user"))

        if results is None:
            results = list(Result.objects.filter(ladder=ladder))

        results_by_player = defaultdict(list)
        results_by_pair = {}
        for r in results:
            if getattr(r, "ladder_id", ladder.id) != ladder.id:
                continue
            results_by_player[r.player_id].append(r)
            results_by_pair[(r.player_id, r.opponent_id)] = r.result

        player_names = {
            lg.player.id: lg.player.full_name(authenticated=authenticated)
            for lg in leagues
        }
        player_urls = {
            lg.player.id: reverse("player_history", args=(lg.player.id,))
            for lg in leagues
        }

        rows = []
        for row_idx, league in enumerate(leagues):
            player = league.player
            row_player_name = player_names[player.id]
            player_results = results_by_player.get(player.id, [])
            total, average = cls.calculate_totals_and_average(player_results)

            cells = []
            for col_idx, opp_league in enumerate(leagues):
                opponent = opp_league.player
                if row_idx == col_idx:
                    cells.append({
                        "is_self": True,
                        "player_id": player.id,
                        "opponent_id": opponent.id,
                        "result": None,
                        "h2h_url": None,
                        "h2h_title": None,
                    })
                else:
                    col_opponent_name = player_names[opponent.id]
                    cells.append({
                        "is_self": False,
                        "player_id": player.id,
                        "opponent_id": opponent.id,
                        "opponent_name": col_opponent_name,
                        "result": results_by_pair.get((player.id, opponent.id)),
                        "h2h_url": reverse("head_to_head", args=(player.id, opponent.id)),
                        "h2h_title": f"{row_player_name} vs {col_opponent_name}",
                    })

            rows.append({
                "position": row_idx + 1,
                "league": league,
                "player": player,
                "player_id": player.id,
                "player_name": row_player_name,
                "player_history_url": player_urls[player.id],
                "is_current_user": authenticated and player.user_id == current_user_id,
                "cells": cells,
                "total": total,
                "average": average,
                "matches_played": len(player_results),
            })

        grid = {
            "ladder": ladder,
            "rows": rows,
        }
        ladder.grid = grid
        return grid

    @classmethod
    def build_season_grids(cls, season, ladders=None, results=None, user=None) -> list[Ladder]:
        """
        Build cross-table grids for all divisions in a season, attaching `.grid`
        to each Ladder instance and returning the list of ladders.
        """
        if ladders is None:
            ladders = list(
                Ladder.objects.filter(season=season)
                .select_related("season")
                .prefetch_related("league_set__player__user")
            )
        else:
            ladders = list(ladders)

        if not ladders:
            return ladders

        if results is None:
            results = list(Result.objects.filter(ladder__season=season))

        results_by_ladder = defaultdict(list)
        for r in results:
            results_by_ladder[r.ladder_id].append(r)

        for ladder in ladders:
            cls.build_ladder_grid(
                ladder,
                user=user,
                results=results_by_ladder.get(ladder.id, []),
            )

        return ladders
