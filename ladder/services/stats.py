from collections import Counter
import datetime
from django.db.models import Case, Count, F, FloatField, Max, Q, Sum, Value, When
from django.utils.timezone import now

from ladder.models import Ladder, League, Player, Result, Season
from ladder.services.centile import CentileService


class ClubStatsService:
    """
    Service for computing club-wide statistics and leaderboards across
    all-time or filtered time periods without N+1 queries.
    """

    DEFAULT_PAGE_SIZE = 10
    MAX_LEADERBOARD_ROWS = 100

    @classmethod
    def _format_player_name(cls, first_name: str, last_name: str, authenticated: bool) -> str:
        p = Player(first_name=first_name or "", last_name=last_name or "")
        return p.full_name(authenticated=authenticated)

    @classmethod
    def resolve_filter(cls, all_seasons: list, period: str = "all", year=None, season_id=None) -> dict:
        """
        Determines which published seasons belong to the active time/era filter,
        along with display labels and minimum round thresholds for Completion %.
        """
        if not all_seasons:
            return {
                "filter_type": "all",
                "period": "all",
                "selected_year": None,
                "selected_season_id": None,
                "seasons": [],
                "filter_label": "All-Time",
                "min_rounds": 5,
            }

        # 1. Specific Season filter
        if season_id:
            try:
                sid = int(season_id)
                matched = [s for s in all_seasons if s.id == sid]
                if matched:
                    s = matched[0]
                    return {
                        "filter_type": "season",
                        "period": None,
                        "selected_year": None,
                        "selected_season_id": s.id,
                        "seasons": matched,
                        "filter_label": f"{s.start_date.year} Round {s.season_round}",
                        "min_rounds": 1,
                    }
            except (ValueError, TypeError):
                pass

        # 2. Specific Year filter
        if year:
            try:
                yr = int(year)
                matched = [s for s in all_seasons if s.start_date.year == yr]
                if matched:
                    return {
                        "filter_type": "year",
                        "period": None,
                        "selected_year": yr,
                        "selected_season_id": None,
                        "seasons": matched,
                        "filter_label": f"{yr} ({len(matched)} round{'s' if len(matched) != 1 else ''})",
                        "min_rounds": min(2, len(matched)),
                    }
            except (ValueError, TypeError):
                pass

        # 3. Preset period filter ('all', '5y', '12m')
        latest_date = max(now().date(), all_seasons[0].end_date)

        if period == "12m":
            cutoff = latest_date - datetime.timedelta(days=365)
            matched = [s for s in all_seasons if s.end_date >= cutoff]
            return {
                "filter_type": "period",
                "period": "12m",
                "selected_year": None,
                "selected_season_id": None,
                "seasons": matched,
                "filter_label": "Past 12 Months",
                "min_rounds": max(1, min(2, len(matched))),
            }

        if period == "5y":
            cutoff = latest_date - datetime.timedelta(days=5 * 365)
            matched = [s for s in all_seasons if s.end_date >= cutoff]
            return {
                "filter_type": "period",
                "period": "5y",
                "selected_year": None,
                "selected_season_id": None,
                "seasons": matched,
                "filter_label": "Past 5 Years",
                "min_rounds": max(1, min(5, len(matched))),
            }

        # Default: All-Time
        return {
            "filter_type": "period",
            "period": "all",
            "selected_year": None,
            "selected_season_id": None,
            "seasons": all_seasons,
            "filter_label": "All-Time",
            "min_rounds": max(1, min(5, len(all_seasons))),
        }

    @classmethod
    def get_club_stats(
        cls,
        period: str = "all",
        year=None,
        season_id=None,
        authenticated: bool = False,
        max_rows: int = MAX_LEADERBOARD_ROWS,
    ) -> dict:
        """
        Computes summary KPIs and all 7 leaderboards for the selected time window.
        """
        all_seasons = list(
            Season.objects.filter(is_draft=False).order_by("-start_date", "-season_round")
        )
        available_years = sorted({s.start_date.year for s in all_seasons}, reverse=True)

        filter_info = cls.resolve_filter(
            all_seasons=all_seasons,
            period=period,
            year=year,
            season_id=season_id,
        )
        filtered_seasons = filter_info["seasons"]
        season_ids = {s.id for s in filtered_seasons}
        min_rounds = filter_info["min_rounds"]

        if not season_ids:
            return {
                "filter": filter_info,
                "available_years": available_years,
                "available_seasons": all_seasons,
                "summary": {
                    "seasons_count": 0,
                    "divisions_count": 0,
                    "matches_played": 0,
                    "active_players": 0,
                },
                "leaderboards": {
                    "most_won": [],
                    "most_played": [],
                    "most_points": [],
                    "most_titles": [],
                    "highest_completion": [],
                    "top_rivalries": [],
                    "best_centile": [],
                },
                "page_size": cls.DEFAULT_PAGE_SIZE,
            }

        # 1. Bulk aggregate match & point stats per player in a single query
        points_expr = Case(
            When(result=9, then=Value(12.0)),  # 9 games + 2 win + 1 play = 12 pts
            default=F("result") + Value(1.0),   # loser games + 1 play pt
            output_field=FloatField(),
        )

        player_rows = list(
            Result.objects.filter(
                ladder__season_id__in=season_ids,
                ladder__season__is_draft=False,
            )
            .values("player_id", "player__first_name", "player__last_name")
            .annotate(
                played=Count("id"),
                won=Count("id", filter=Q(result=9)),
                total_points=Sum(points_expr),
            )
        )

        total_result_rows = 0
        player_stats_list = []
        played_by_player_id = {}

        for row in player_rows:
            played = int(row["played"] or 0)
            if played <= 0:
                continue
            won = int(row["won"] or 0)
            pts = float(row["total_points"] or 0.0)
            win_rate = (won / played) * 100.0
            avg_points = pts / played
            total_result_rows += played
            played_by_player_id[row["player_id"]] = played

            name = cls._format_player_name(
                row["player__first_name"],
                row["player__last_name"],
                authenticated=authenticated,
            )

            player_stats_list.append({
                "player_id": row["player_id"],
                "player_name": name,
                "played": played,
                "won": won,
                "lost": played - won,
                "total_points": int(round(pts)),
                "win_rate": win_rate,
                "win_rate_display": f"{win_rate:.1f}%",
                "avg_points": avg_points,
                "avg_points_display": f"{avg_points:.2f}",
            })

        # Count distinct active players and divisions for the period
        divisions_count = Ladder.objects.filter(season_id__in=season_ids).count()
        active_players_count = (
            League.objects.filter(ladder__season_id__in=season_ids)
            .values("player_id")
            .distinct()
            .count()
        )

        # Build the first 3 match/points leaderboards from player_stats_list
        most_won = sorted(
            [p for p in player_stats_list if p["won"] > 0],
            key=lambda x: (-x["won"], -x["win_rate"], -x["played"], x["player_name"]),
        )[:max_rows]

        most_played = sorted(
            player_stats_list,
            key=lambda x: (-x["played"], -x["won"], x["player_name"]),
        )[:max_rows]

        most_points = sorted(
            [p for p in player_stats_list if p["total_points"] > 0],
            key=lambda x: (-x["total_points"], -x["won"], -x["played"], x["player_name"]),
        )[:max_rows]

        # 2. Division Titles, Highest Match Completion %, & Best Centile (single pass via CentileService)
        most_titles, highest_completion, best_centile = cls._build_standing_leaderboards(
            season_ids=season_ids,
            played_by_player_id=played_by_player_id,
            min_rounds=min_rounds,
            authenticated=authenticated,
            max_rows=max_rows,
        )

        # 3. Most Played Head-to-Head Rivalries (single query on Result)
        top_rivalries = cls._build_rivalries_leaderboard(
            season_ids=season_ids,
            authenticated=authenticated,
            max_rows=max_rows,
        )

        return {
            "filter": filter_info,
            "available_years": available_years,
            "available_seasons": all_seasons,
            "summary": {
                "seasons_count": len(season_ids),
                "divisions_count": divisions_count,
                "matches_played": total_result_rows // 2,
                "active_players": active_players_count,
            },
            "leaderboards": {
                "most_won": most_won,
                "most_played": most_played,
                "most_points": most_points,
                "most_titles": most_titles,
                "highest_completion": highest_completion,
                "top_rivalries": top_rivalries,
                "best_centile": best_centile,
            },
            "page_size": cls.DEFAULT_PAGE_SIZE,
        }

    @classmethod
    def _build_standing_leaderboards(
        cls,
        season_ids: set,
        played_by_player_id: dict,
        min_rounds: int,
        authenticated: bool,
        max_rows: int,
    ) -> tuple[list, list, list]:
        """
        Reuses CentileService.compute_season_rankings(season_ids, include_division_winners=True)
        and CentileService.calculate_centile(rank, total_players) to build:
          - most_titles: Most Division Titles (with badges for each division won)
          - highest_completion: Highest Match Completion % (played / scheduled matches)
          - best_centile: Best Centile & Top Finishers
        """
        season_totals, rank_by_league_id, division_winner_league_ids, division_sizes = (
            CentileService.compute_season_rankings(season_ids, include_division_winners=True)
        )
        if not season_totals:
            return [], [], []

        league_rows = (
            League.objects.filter(
                ladder__season_id__in=season_ids,
                ladder__season__is_draft=False,
            )
            .values(
                "id",
                "player_id",
                "player__first_name",
                "player__last_name",
                "ladder__season_id",
                "ladder__season__start_date",
                "ladder__season__season_round",
                "ladder__division",
            )
        )

        by_player = {}

        for lg in league_rows:
            lid = lg["id"]
            sid = lg["ladder__season_id"]
            total_players = season_totals.get(sid, 0)
            rank = rank_by_league_id.get(lid, 0)
            centile = CentileService.calculate_centile(rank, total_players)
            if centile is None:
                continue

            pid = lg["player_id"]
            year = lg["ladder__season__start_date"].year
            s_round = lg["ladder__season__season_round"]
            div = lg["ladder__division"]
            is_div_winner = lid in division_winner_league_ids
            is_div1_winner = is_div_winner and (div == 1)
            div_size = division_sizes.get((sid, div), 0)
            scheduled_in_div = max(0, div_size - 1)

            rec = by_player.get(pid)
            if rec is None:
                div_counts = Counter()
                if is_div_winner:
                    div_counts[div] += 1
                rec = {
                    "player_id": pid,
                    "player_name": cls._format_player_name(
                        lg["player__first_name"],
                        lg["player__last_name"],
                        authenticated=authenticated,
                    ),
                    "best_centile": centile,
                    "best_rank": rank,
                    "best_total_players": total_players,
                    "best_year": year,
                    "best_round": s_round,
                    "best_division": div,
                    "peak_count": 1,
                    "sum_centile": centile,
                    "seasons_played": 1,
                    "division_titles": 1 if is_div_winner else 0,
                    "div1_titles": 1 if is_div1_winner else 0,
                    "divisions_won_counts": div_counts,
                    "scheduled_matches": scheduled_in_div,
                }
                by_player[pid] = rec
            else:
                rec["seasons_played"] += 1
                rec["sum_centile"] += centile
                rec["scheduled_matches"] += scheduled_in_div
                if is_div_winner:
                    rec["division_titles"] += 1
                    rec["divisions_won_counts"][div] += 1
                if is_div1_winner:
                    rec["div1_titles"] += 1

                # Check if this entry matches or beats their best standing
                new_standing = (centile, -rank)
                best_standing = (rec["best_centile"], -rec["best_rank"])

                if new_standing > best_standing:
                    rec.update({
                        "best_centile": centile,
                        "best_rank": rank,
                        "best_total_players": total_players,
                        "best_year": year,
                        "best_round": s_round,
                        "best_division": div,
                        "peak_count": 1,
                    })
                elif new_standing == best_standing:
                    rec["peak_count"] += 1
                    if (year, s_round) > (rec["best_year"], rec["best_round"]):
                        rec.update({
                            "best_total_players": total_players,
                            "best_year": year,
                            "best_round": s_round,
                            "best_division": div,
                        })

        for rec in by_player.values():
            avg_c = rec["sum_centile"] / rec["seasons_played"]
            rec["avg_centile"] = avg_c
            rec["avg_centile_display"] = f"{avg_c:.1f}%"
            title_rate = (rec["division_titles"] / rec["seasons_played"]) * 100.0
            rec["title_rate"] = title_rate
            rec["title_rate_display"] = f"{title_rate:.0f}%"

            # Format badges for every division won (sorted from highest tier Div 1 downwards)
            div_counts = rec.pop("divisions_won_counts")
            rec["divisions_won_badges"] = [
                {
                    "division": d,
                    "count": cnt,
                    "is_div1": (d == 1),
                    "label": f"Div {d}" if cnt == 1 else f"Div {d} \u00d7{cnt}",
                }
                for d, cnt in sorted(div_counts.items())
            ]

            # Match completion stats
            played = played_by_player_id.get(rec["player_id"], 0)
            scheduled = rec["scheduled_matches"]
            rec["played_matches"] = played
            if scheduled > 0:
                comp_rate = min(100.0, (played / scheduled) * 100.0)
            else:
                comp_rate = 0.0
            rec["completion_rate"] = comp_rate
            rec["completion_rate_display"] = f"{comp_rate:.1f}%"

        most_titles = sorted(
            [p for p in by_player.values() if p["division_titles"] > 0],
            key=lambda x: (
                -x["division_titles"],
                -x["div1_titles"],
                -x["title_rate"],
                -x["avg_centile"],
                x["player_name"],
            ),
        )[:max_rows]

        highest_completion = sorted(
            [
                p
                for p in by_player.values()
                if p["seasons_played"] >= min_rounds and p["scheduled_matches"] > 0 and p["played_matches"] > 0
            ],
            key=lambda x: (
                -x["completion_rate"],
                -x["played_matches"],
                -x["seasons_played"],
                x["player_name"],
            ),
        )[:max_rows]

        best_centile = sorted(
            by_player.values(),
            key=lambda x: (
                -x["best_centile"],
                x["best_rank"],
                -x["peak_count"],
                -x["avg_centile"],
                -x["seasons_played"],
                x["player_name"],
            ),
        )[:max_rows]

        return most_titles, highest_completion, best_centile

    @classmethod
    def _build_rivalries_leaderboard(
        cls, season_ids: set, authenticated: bool, max_rows: int
    ) -> list:
        """
        Finds the most frequently played head-to-head matchups in the selected period
        in a single aggregated query.
        """
        win_rows = (
            Result.objects.filter(
                ladder__season_id__in=season_ids,
                ladder__season__is_draft=False,
                result=9,
            )
            .values(
                "player_id",
                "player__first_name",
                "player__last_name",
                "opponent_id",
                "opponent__first_name",
                "opponent__last_name",
            )
            .annotate(
                wins=Count("id"),
                last_played=Max("date_added"),
            )
        )

        pairs = {}
        for row in win_rows:
            p1_id = row["player_id"]
            p2_id = row["opponent_id"]
            if p1_id == p2_id:
                continue

            pair_key = (min(p1_id, p2_id), max(p1_id, p2_id))
            rec = pairs.get(pair_key)
            p1_name = cls._format_player_name(
                row["player__first_name"],
                row["player__last_name"],
                authenticated=authenticated,
            )
            p2_name = cls._format_player_name(
                row["opponent__first_name"],
                row["opponent__last_name"],
                authenticated=authenticated,
            )

            if rec is None:
                if p1_id < p2_id:
                    rec = {
                        "low_id": p1_id,
                        "low_name": p1_name,
                        "low_wins": int(row["wins"] or 0),
                        "high_id": p2_id,
                        "high_name": p2_name,
                        "high_wins": 0,
                        "last_played": row["last_played"],
                    }
                else:
                    rec = {
                        "low_id": p2_id,
                        "low_name": p2_name,
                        "low_wins": 0,
                        "high_id": p1_id,
                        "high_name": p1_name,
                        "high_wins": int(row["wins"] or 0),
                        "last_played": row["last_played"],
                    }
                pairs[pair_key] = rec
            else:
                if p1_id == rec["low_id"]:
                    rec["low_wins"] += int(row["wins"] or 0)
                else:
                    rec["high_wins"] += int(row["wins"] or 0)
                if row["last_played"] and (
                    rec["last_played"] is None or row["last_played"] > rec["last_played"]
                ):
                    rec["last_played"] = row["last_played"]

        rivalries = []
        for rec in pairs.values():
            total_matches = rec["low_wins"] + rec["high_wins"]
            if total_matches < 2:
                continue

            # Put the player with more wins in the rivalry first
            if (rec["low_wins"], rec["high_name"]) >= (rec["high_wins"], rec["low_name"]):
                a_id, a_name, a_wins = rec["low_id"], rec["low_name"], rec["low_wins"]
                b_id, b_name, b_wins = rec["high_id"], rec["high_name"], rec["high_wins"]
            else:
                a_id, a_name, a_wins = rec["high_id"], rec["high_name"], rec["high_wins"]
                b_id, b_name, b_wins = rec["low_id"], rec["low_name"], rec["low_wins"]

            rivalries.append({
                "player_a_id": a_id,
                "player_a_name": a_name,
                "player_a_wins": a_wins,
                "player_b_id": b_id,
                "player_b_name": b_name,
                "player_b_wins": b_wins,
                "matches_played": total_matches,
                "last_played": rec["last_played"],
            })

        rivalries.sort(
            key=lambda x: (
                -x["matches_played"],
                -(x["last_played"].toordinal() if x["last_played"] else 0),
                x["player_a_name"],
                x["player_b_name"],
            )
        )
        return rivalries[:max_rows]
