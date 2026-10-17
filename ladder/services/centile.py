from collections import defaultdict
from django.db.models import Case, When, Value, FloatField, F, Sum

from ladder.models import League, Result


class CentileService:
    """
    Encapsulates the calculation of a player's centile standing across published seasons.
    
    Centile calculation:
      - Within each division of a season, players are ranked by total points scored (descending).
      - Ties in points are broken by initial league sort_order.
      - A player's overall club rank for the season is:
          (total players in higher divisions) + (player's rank within their division).
      - Centile is: round((rank / total_season_players) * 100).
    """

    @classmethod
    def get_player_centile_history(cls, player) -> dict:
        """
        Returns centile metrics and chart data for the given player.
        """
        player_leagues = list(
            player.league_set
            .filter(ladder__season__is_draft=False)
            .select_related('ladder__season')
            .order_by('ladder__season__start_date', 'ladder__season__season_round', 'ladder__division')
        )

        if not player_leagues:
            return {
                'by_league_id': {},
                'best_centile': "- %",
                'chart_data': [],
            }

        season_ids = {lg.ladder.season_id for lg in player_leagues}

        # 1. Fetch total points for all players across relevant seasons in a single query
        points_expr = Case(
            When(result=9, then=Value(12.0)),  # 9 games + 2 win + 1 play = 12 pts
            default=F('result') + Value(1.0),   # loser games + 1 play pt
            output_field=FloatField(),
        )
        points_agg = (
            Result.objects
            .filter(ladder__season_id__in=season_ids, ladder__season__is_draft=False)
            .values('ladder__season_id', 'ladder__division', 'player_id')
            .annotate(total=Sum(points_expr))
        )
        points_map = {
            (row['ladder__season_id'], row['ladder__division'], row['player_id']): float(row['total'] or 0.0)
            for row in points_agg
        }

        # 2. Fetch all league entries in these seasons to compute division & club ranks
        all_season_leagues = (
            League.objects
            .filter(ladder__season_id__in=season_ids, ladder__season__is_draft=False)
            .values('id', 'player_id', 'ladder__season_id', 'ladder__division', 'sort_order')
            .order_by('ladder__season_id', 'ladder__division', 'sort_order', 'id')
        )

        # 3. Group leagues by season and division
        season_div_leagues = defaultdict(lambda: defaultdict(list))
        for lg in all_season_leagues:
            season_div_leagues[lg['ladder__season_id']][lg['ladder__division']].append(lg)

        # 4. Rank players across the whole season:
        #    For each division (in ascending division order):
        #      Sort players by points (descending), then sort_order, then id
        season_totals = {}
        rank_by_league_id = {}

        for season_id, divisions in season_div_leagues.items():
            current_rank = 0
            for div_num in sorted(divisions.keys()):
                div_leagues = divisions[div_num]
                div_leagues.sort(
                    key=lambda x: (
                        -points_map.get((season_id, div_num, x['player_id']), 0.0),
                        x['sort_order'],
                        x['id']
                    )
                )
                for item in div_leagues:
                    current_rank += 1
                    rank_by_league_id[item['id']] = current_rank
            season_totals[season_id] = current_rank

        by_league_id = {}
        chart_data = []
        best_centile_val = None

        for lg in player_leagues:
            season_id = lg.ladder.season_id
            total_players = season_totals.get(season_id, 0)
            rank = rank_by_league_id.get(lg.id, 0)
            if total_players > 0 and rank > 0:
                centile = round((rank / total_players) * 100)
                if best_centile_val is None or centile < best_centile_val:
                    best_centile_val = centile
            else:
                centile = None

            season_obj = lg.ladder.season
            entry = {
                'league_id': lg.id,
                'season_label': f"{season_obj.start_date.year} R{season_obj.season_round}",
                'season_name': str(season_obj),
                'division': lg.ladder.division,
                'rank': rank,
                'total_players': total_players,
                'centile': centile,
            }
            by_league_id[lg.id] = entry
            if centile is not None:
                chart_data.append(entry)

        best_centile_str = f"{best_centile_val}%" if best_centile_val is not None else "- %"

        return {
            'by_league_id': by_league_id,
            'best_centile': best_centile_str,
            'chart_data': chart_data,
        }
