from collections import defaultdict
from django.db.models import Case, Count, F, IntegerField, Max, Min, Q, Value, When

from ladder.models import Player, Result
from ladder.services.centile import CentileService


class PlayerStatsService:
    """
    Service for computing player profile statistics, career insights,
    head-to-head summaries, season history, and head-to-head matchup details
    without N+1 queries.
    """

    DEFAULT_H2H_PAGE_SIZE = 10
    DEFAULT_HISTORY_PAGE_SIZE = 10

    @staticmethod
    def format_player_name(first_name: str, last_name: str, authenticated: bool) -> str:
        p = Player(
            first_name=(first_name or "").strip(),
            last_name=(last_name or "").strip(),
        )
        return p.full_name(authenticated=authenticated)

    @classmethod
    def get_player_profile(cls, player: Player, authenticated: bool = False) -> dict:
        """
        Builds the complete context for the player history/profile page.
        """
        # 1. Fetch published league entries for the player
        league_list = list(
            player.league_set.filter(ladder__season__is_draft=False)
            .select_related("ladder__season")
            .prefetch_related("ladder__league_set")
            .order_by(
                "-ladder__season__start_date",
                "-ladder__season__season_round",
                "ladder__division",
            )
        )

        # 2. Compute centile history & division rankings across all seasons the player entered
        centile_history = CentileService.get_player_centile_history(player)
        season_ids = {lg.ladder.season_id for lg in league_list}
        _, _, division_winner_league_ids, _ = CentileService.compute_season_rankings(
            season_ids, include_division_winners=True
        )

        by_league_id = centile_history["by_league_id"]
        centiles_list = []
        division_titles = 0
        divisions_won_counts = defaultdict(int)
        highest_division = None
        scheduled_matches_total = 0

        for lg in league_list:
            lg.player = player
            div = lg.ladder.division
            if highest_division is None or div < highest_division:
                highest_division = div

            div_size = len(lg.ladder.league_set.all())
            scheduled_in_lg = max(0, div_size - 1)
            scheduled_matches_total += scheduled_in_lg
            lg.scheduled_matches = scheduled_in_lg

            is_winner = lg.id in division_winner_league_ids
            lg.is_division_winner = is_winner
            if is_winner:
                division_titles += 1
                divisions_won_counts[div] += 1

            info = by_league_id.get(lg.id)
            if info and info["centile"] is not None:
                lg.centile = info["centile"]
                lg.centile_rank = info["rank"]
                lg.centile_total = info["total_players"]
                centiles_list.append(info["centile"])
            else:
                lg.centile = None
                lg.centile_rank = None
                lg.centile_total = None

        divisions_won_badges = [
            {
                "division": d,
                "count": cnt,
                "is_div1": (d == 1),
                "label": f"Div {d}" if cnt == 1 else f"Div {d} \u00d7{cnt}",
            }
            for d, cnt in sorted(divisions_won_counts.items())
        ]

        # 3. Fetch all player results in one query (chronological order for streak calculations)
        all_results = list(
            Result.objects.filter(player=player)
            .select_related("opponent", "ladder__season")
            .order_by("date_added", "id")
        )

        # Fetch mirror loser rows where this player won (so we know opponent's losing score)
        mirror_loser_rows = (
            Result.objects.filter(opponent=player, result__lt=9)
            .values_list("ladder_id", "player_id", "result")
        )
        mirror_score_map = {
            (ladder_id, opp_id): int(score or 0)
            for ladder_id, opp_id, score in mirror_loser_rows
        }

        # 4. Aggregate career stats, per-ladder stats, H2H records, and insights
        player_stats = player.player_stats()
        player_stats["best_centile"] = centile_history["best_centile"]
        player_stats["seasons_played"] = len(league_list)
        player_stats["division_titles"] = division_titles
        player_stats["divisions_won_badges"] = divisions_won_badges
        player_stats["highest_division"] = highest_division if highest_division is not None else "-"
        player_stats["scheduled_matches"] = scheduled_matches_total
        player_stats["avg_centile"] = (
            f"{sum(centiles_list) / len(centiles_list):.1f}%" if centiles_list else "- %"
        )

        if league_list:
            years = [lg.ladder.season.start_date.year for lg in league_list]
            player_stats["first_year"] = min(years)
            player_stats["last_year"] = max(years)
        else:
            player_stats["first_year"] = None
            player_stats["last_year"] = None

        # Find peak standing details
        best_centile_num = -1
        best_rank = None
        best_total_players = None
        best_season_label = None
        for item in centile_history["chart_data"]:
            if best_rank is None or (item["centile"], -item["rank"]) > (
                best_centile_num,
                -(best_rank or 999999),
            ):
                best_centile_num = item["centile"]
                best_rank = item["rank"]
                best_total_players = item["total_players"]
                best_season_label = f"{item['season_label']} \u00b7 Div {item['division']}"

        player_stats["best_rank"] = best_rank
        player_stats["best_total_players"] = best_total_players
        player_stats["best_season_label"] = best_season_label

        # Group results by opponent for Head-to-Head and compute match-level insights
        h2h_by_opponent = {}
        results_by_ladder = defaultdict(list)

        won_count = 0
        total_points = 0
        total_games_won = 0
        total_games_lost = 0
        clutch_played = 0
        clutch_won = 0
        dominant_wins = 0
        bagels_won = 0
        win_loser_scores = []
        loss_player_scores = []

        longest_win_streak = 0
        current_win_streak = 0
        recent_matches = []

        for r in all_results:
            if r.ladder.season.is_draft:
                continue

            results_by_ladder[r.ladder_id].append(r)
            is_win = r.result == 9

            if is_win:
                my_games = 9
                opp_games = mirror_score_map.get((r.ladder_id, r.opponent_id), 0)
                pts = 12
                won_count += 1
                current_win_streak += 1
                if current_win_streak > longest_win_streak:
                    longest_win_streak = current_win_streak
                win_loser_scores.append(opp_games)

                if opp_games == 0:
                    bagels_won += 1
                if opp_games <= 2:
                    dominant_wins += 1
                if opp_games >= 7:
                    clutch_played += 1
                    clutch_won += 1
            else:
                my_games = int(r.result or 0)
                opp_games = 9
                pts = my_games + 1
                current_win_streak = 0
                loss_player_scores.append(my_games)

                if my_games >= 7:
                    clutch_played += 1

            total_points += pts
            total_games_won += my_games
            total_games_lost += opp_games

            opp_id = r.opponent_id
            opp_first = r.opponent.first_name or ""
            opp_last = r.opponent.last_name or ""
            opp_name = cls.format_player_name(opp_first, opp_last, authenticated=authenticated)

            h_rec = h2h_by_opponent.get(opp_id)
            if h_rec is None:
                h_rec = {
                    "opponent": opp_id,
                    "opponent__first_name": opp_first,
                    "opponent__last_name": opp_last,
                    "opponent_name": opp_name,
                    "times_played": 0,
                    "won": 0,
                    "lost": 0,
                    "last_played": r.date_added,
                }
                h2h_by_opponent[opp_id] = h_rec

            h_rec["times_played"] += 1
            if is_win:
                h_rec["won"] += 1
            else:
                h_rec["lost"] += 1
            if r.date_added and (h_rec["last_played"] is None or r.date_added > h_rec["last_played"]):
                h_rec["last_played"] = r.date_added

            recent_matches.append({
                "won": is_win,
                "my_games": my_games,
                "opp_games": opp_games,
                "score_display": f"{my_games}\u2013{opp_games}",
                "opponent_id": opp_id,
                "opponent_name": opp_name,
                "date_added": r.date_added,
                "season_label": f"{r.ladder.season.start_date.year} R{r.ladder.season.season_round}",
            })

        played_total = len(recent_matches)
        player_stats["won"] = won_count
        player_stats["lost"] = max(0, played_total - won_count)
        player_stats["total_points"] = total_points
        player_stats["unique_opponents"] = len(h2h_by_opponent)

        # Finalize H2H rows
        head_list = []
        for h_rec in h2h_by_opponent.values():
            tp = h_rec["times_played"]
            w = h_rec["won"]
            wr = (w / tp) * 100.0 if tp > 0 else 0.0
            h_rec["win_rate"] = wr
            h_rec["win_rate_display"] = f"{wr:.0f}%"
            h_rec["won_played_display"] = f"{w}/{tp}"
            head_list.append(h_rec)

        head_list.sort(
            key=lambda x: (
                -x["times_played"],
                -x["won"],
                -(x["last_played"].toordinal() if x["last_played"] else 0),
                x["opponent_name"],
            )
        )

        # Compute round-level milestones without hitting the database
        full_completion_rounds = 0
        best_round_points = 0
        best_round_label = None

        for lg in league_list:
            lg_results = results_by_ladder.get(lg.ladder_id, [])
            games = len(lg_results)
            lg_won = sum(1 for r in lg_results if r.result == 9)
            lg_points = sum(12.0 if r.result == 9 else (r.result + 1.0) for r in lg_results)
            pointsdivgames = lg_points / games if games > 0 else 0
            percplayed = (
                (games / lg.scheduled_matches * 100.0) if lg.scheduled_matches > 0 else 0
            )
            lg_stats = {
                "total_points": lg_points,
                "games": games,
                "pointsdivgames": pointsdivgames,
                "won_count": lg_won,
                "percplayed": percplayed,
            }
            lg.computed_stats = lg_stats

            pts = int(round(lg_points))
            if pts > best_round_points:
                best_round_points = pts
                best_round_label = (
                    f"{lg.ladder.season.start_date.year} R{lg.ladder.season.season_round} "
                    f"\u00b7 Div {lg.ladder.division}"
                )
            if lg.scheduled_matches > 0 and games >= lg.scheduled_matches:
                full_completion_rounds += 1

        # Build Rivalry Superlatives
        most_played_rival = head_list[0] if head_list else None

        win_rivals = [h for h in head_list if h["won"] > 0]
        favourite_rival = (
            max(
                win_rivals,
                key=lambda x: (x["won"], x["win_rate"], -x["lost"], x["times_played"]),
            )
            if win_rivals
            else None
        )

        loss_rivals = [h for h in head_list if h["lost"] > 0]
        toughest_rival = (
            max(
                loss_rivals,
                key=lambda x: (x["lost"], -x["win_rate"], x["times_played"]),
            )
            if loss_rivals
            else None
        )

        total_games = total_games_won + total_games_lost
        games_win_rate = (total_games_won / total_games * 100.0) if total_games > 0 else 0.0
        clutch_win_rate = (clutch_won / clutch_played * 100.0) if clutch_played > 0 else 0.0
        full_comp_rate = (
            (full_completion_rounds / len(league_list) * 100.0) if league_list else 0.0
        )

        insights = {
            "has_matches": played_total > 0,
            "recent_form": list(reversed(recent_matches[-5:])),  # newest first
            "longest_win_streak": longest_win_streak,
            "current_win_streak": current_win_streak,
            "full_completion_rounds": full_completion_rounds,
            "full_completion_rate": f"{full_comp_rate:.0f}%",
            "best_round_points": best_round_points,
            "best_round_label": best_round_label,
            "clutch_played": clutch_played,
            "clutch_won": clutch_won,
            "clutch_lost": clutch_played - clutch_won,
            "clutch_win_rate": f"{clutch_win_rate:.0f}%",
            "dominant_wins": dominant_wins,
            "bagels_won": bagels_won,
            "total_games_won": total_games_won,
            "total_games_lost": total_games_lost,
            "games_win_rate": f"{games_win_rate:.1f}%",
            "avg_loser_score_in_wins": (
                f"{sum(win_loser_scores) / len(win_loser_scores):.1f}"
                if win_loser_scores
                else "-"
            ),
            "avg_player_score_in_losses": (
                f"{sum(loss_player_scores) / len(loss_player_scores):.1f}"
                if loss_player_scores
                else "-"
            ),
            "most_played_rival": most_played_rival,
            "favourite_rival": favourite_rival,
            "toughest_rival": toughest_rival,
        }

        return {
            "player": player,
            "league_set": league_list,
            "ladder_set": league_list,
            "head": head_list,
            "player_stats": player_stats,
            "insights": insights,
            "centile_chart_data": centile_history["chart_data"],
            "h2h_page_size": cls.DEFAULT_H2H_PAGE_SIZE,
            "history_page_size": cls.DEFAULT_HISTORY_PAGE_SIZE,
        }

    @classmethod
    def get_head_to_head(
        cls, player: Player, opponent: Player, authenticated: bool = False
    ) -> dict:
        """
        Computes detailed head-to-head stats and match history between two players.
        """
        results1 = Result.objects.filter(
            player=player, opponent=opponent, result__lt=9
        ).select_related("ladder__season", "player", "opponent")
        results2 = Result.objects.filter(
            player=opponent, opponent=player, result__lt=9
        ).select_related("ladder__season", "player", "opponent")

        results_qs = (results1 | results2).order_by(
            "-date_added", "-ladder__season__end_date", "-id"
        )
        results_list = list(results_qs)

        won = 0
        lost = 0
        player_games = 0
        opponent_games = 0
        close_matches = 0
        matches = []

        player_name = player.full_name(authenticated=authenticated)
        opponent_name = opponent.full_name(authenticated=authenticated)

        for r in results_list:
            # In a result__lt=9 row, r.opponent is the winner (9) and r.player is the loser (r.result)
            losing_score = int(r.result or 0)
            player_won = r.opponent_id == player.id

            if player_won:
                won += 1
                p_score = 9
                o_score = losing_score
            else:
                lost += 1
                p_score = losing_score
                o_score = 9

            player_games += p_score
            opponent_games += o_score
            if losing_score >= 7:
                close_matches += 1

            season = r.ladder.season
            matches.append({
                "result_obj": r,
                "date_added": r.date_added,
                "year": season.start_date.year,
                "season_round": season.season_round,
                "division": r.ladder.division,
                "ladder_full": f"{season.start_date.year} Round {season.season_round} \u00b7 Division {r.ladder.division}",
                "ladder_short": f"{season.start_date.year} R{season.season_round} \u00b7 Div {r.ladder.division}",
                "player_won": player_won,
                "winner_id": r.opponent_id,
                "winner_name": r.opponent.full_name(authenticated=authenticated),
                "loser_id": r.player_id,
                "loser_name": r.player.full_name(authenticated=authenticated),
                "losing_score": losing_score,
                "player_score": p_score,
                "opponent_score": o_score,
                "score_display": f"9\u2013{losing_score}",
                "is_close": losing_score >= 7,
            })

        played = won + lost
        player_win_pct = round((won / played) * 100) if played > 0 else 0
        opponent_win_pct = (100 - player_win_pct) if played > 0 else 0

        stats = {
            "played": played,
            "won": won,
            "lost": lost,
            "player_win_pct": player_win_pct,
            "opponent_win_pct": opponent_win_pct,
            "player_games": player_games,
            "opponent_games": opponent_games,
            "close_matches": close_matches,
            "first_played": matches[-1]["date_added"] if matches else None,
            "last_played": matches[0]["date_added"] if matches else None,
        }

        return {
            "player": player,
            "opponent": opponent,
            "player_name": player_name,
            "opponent_name": opponent_name,
            "stats": stats,
            "results": results_list,
            "matches": matches,
        }

    @classmethod
    def search_players(cls, query: str, authenticated: bool = False, limit: int = 25) -> list:
        """
        Searches players by name with relevance ranking (prefix matches first,
        then recently active players) and surname enumeration protection for anonymous users.
        """
        terms = (query or "").split()
        if not terms:
            return []

        qs = Player.objects.all()

        if authenticated:
            for term in terms:
                qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))
        else:
            if len(terms) == 1:
                qs = qs.filter(first_name__icontains=terms[0])
            else:
                first = terms[0]
                last_token = terms[-1].rstrip(".")
                if len(last_token) == 1:
                    qs = qs.filter(
                        first_name__icontains=first,
                        last_name__istartswith=last_token,
                    )
                else:
                    qs = qs.filter(first_name__icontains=first)

        first_term = terms[0]
        published_filter = Q(league__ladder__season__is_draft=False)

        qs = qs.annotate(
            match_priority=Case(
                When(first_name__istartswith=first_term, then=Value(0)),
                When(last_name__istartswith=first_term, then=Value(1)),
                When(first_name__icontains=first_term, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            ),
            seasons_played=Count("league", filter=published_filter, distinct=True),
            first_season_date=Min("league__ladder__season__start_date", filter=published_filter),
            last_season_date=Max("league__ladder__season__start_date", filter=published_filter),
        ).order_by(
            "match_priority",
            F("last_season_date").desc(nulls_last=True),
            "-seasons_played",
            "first_name",
            "last_name",
        )

        players = list(qs[:limit])
        for p in players:
            p.is_authed = authenticated
        return players

    @classmethod
    def autocomplete_players(cls, query: str, authenticated: bool = False, limit: int = 10) -> list:
        """
        Returns autocomplete option dicts [{'id': id, 'label': masked_name}] for navbar search.
        """
        players = cls.search_players(query=query, authenticated=authenticated, limit=limit)
        return [
            {"id": p.id, "label": p.full_name(authenticated=authenticated)}
            for p in players
        ]
