import datetime
from django.urls import reverse
from django.utils.timezone import now


class MatchService:
    """
    Service for normalizing, querying, and formatting match results.
    """

    @classmethod
    def get_recent_results_for_season(cls, season, user=None, limit: int = 50):
        """
        Returns up to `limit` completed matches in a season, newest first.
        Normalizes reciprocal Result rows into single match items with winner first,
        precomputes URLs, relative dates, and H2H modal attributes.
        """
        from ladder.models import Result

        raw_results = (
            Result.objects
            .filter(ladder__season=season)
            .select_related('player', 'opponent', 'ladder', 'ladder__season')
            .order_by('-date_added', '-id')
        )[:limit * 3]

        return cls.build_recent_results(raw_results, user=user, limit=limit)

    @classmethod
    def get_recent_results_for_ladder(cls, ladder, user=None, limit: int = 50):
        """
        Returns up to `limit` completed matches in a division, newest first.
        """
        from ladder.models import Result

        raw_results = (
            Result.objects
            .filter(ladder=ladder)
            .select_related('player', 'opponent', 'ladder', 'ladder__season')
            .order_by('-date_added', '-id')
        )[:limit * 3]

        return cls.build_recent_results(raw_results, user=user, limit=limit)

    @classmethod
    def build_recent_results(cls, raw_results, user=None, limit: int = 50):
        """
        Normalizes reciprocal Result rows into single match dicts with winner first,
        precomputed URLs, relative dates, and H2H modal attributes.
        """
        authenticated = getattr(user, 'is_authenticated', False)
        today = now().date()

        pairs = {}
        for r in raw_results:
            pair_key = (r.ladder_id, min(r.player_id, r.opponent_id), max(r.player_id, r.opponent_id))
            if pair_key not in pairs:
                pairs[pair_key] = []
            if len(pairs[pair_key]) < 2:
                pairs[pair_key].append(r)

        matches = []
        for pair_key, rows in pairs.items():
            if len(rows) < 2:
                continue
            r1, r2 = rows[0], rows[1]
            reason = r1.incomplete_reason or r2.incomplete_reason
            is_incomplete = (r1.result < 9 and r2.result < 9) or reason == 'time'
            is_injury = (reason == 'injury') and (r1.result == 9 or r2.result == 9)

            if is_incomplete:
                if (r1.result, -r1.player_id) >= (r2.result, -r2.player_id):
                    winner, loser = r1.player, r2.player
                    winner_score, loser_score = r1.result, r2.result
                else:
                    winner, loser = r2.player, r1.player
                    winner_score, loser_score = r2.result, r1.result
                score_display = f"{winner_score} – {loser_score} (Inc.)"
            elif r1.result == 9:
                winner, loser = r1.player, r2.player
                winner_score, loser_score = r1.result, r2.result
                score_display = f"{winner_score} – {loser_score} (Ret.)" if is_injury else f"{winner_score} – {loser_score}"
            elif r2.result == 9:
                winner, loser = r2.player, r1.player
                winner_score, loser_score = r2.result, r1.result
                score_display = f"{winner_score} – {loser_score} (Ret.)" if is_injury else f"{winner_score} – {loser_score}"
            else:
                continue

            ladder = r1.ladder
            date_added = r1.date_added

            # Relative date calculation
            if date_added == today:
                date_display = "Today"
            elif date_added == today - datetime.timedelta(days=1):
                date_display = "Yesterday"
            elif date_added.year == today.year:
                date_display = f"{date_added.strftime('%a')} {date_added.day} {date_added.strftime('%b')}"
            else:
                date_display = f"{date_added.day} {date_added.strftime('%b %Y')}"

            date_full = f"{date_added.strftime('%A')}, {date_added.day} {date_added.strftime('%B %Y')}"

            winner_name = winner.full_name(authenticated=authenticated)
            loser_name = loser.full_name(authenticated=authenticated)

            h2h_url = reverse('head_to_head', kwargs={'player_id': winner.id, 'opponent_id': loser.id})
            division_url = reverse('ladder', kwargs={
                'year': ladder.season.start_date.year,
                'season_round': ladder.season.season_round,
                'division_id': ladder.division,
            })

            max_id = max(r1.id, r2.id)

            matches.append({
                'winner': winner,
                'winner_id': winner.id,
                'winner_name': winner_name,
                'loser': loser,
                'loser_id': loser.id,
                'loser_name': loser_name,
                'winner_score': winner_score,
                'loser_score': loser_score,
                'score_display': score_display,
                'is_incomplete': is_incomplete,
                'is_injury': is_injury,
                'incomplete_reason': reason or ('time' if is_incomplete else None),
                'division': ladder.division,
                'division_url': division_url,
                'date_added': date_added,
                'date_display': date_display,
                'date_full': date_full,
                'h2h_url': h2h_url,
                'h2h_title': f"{winner_name} vs {loser_name}",
                '_sort_key': (date_added, max_id),
            })

        matches.sort(key=lambda m: m['_sort_key'], reverse=True)
        return matches[:limit]
