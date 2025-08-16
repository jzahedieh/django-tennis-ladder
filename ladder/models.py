from datetime import date
import uuid
from django.db import models
from django.db.models import Avg, Count
from django.contrib.auth.models import User
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
import datetime

from django.utils.timezone import now


class Season(models.Model):
    name = models.CharField(max_length=150)
    start_date = models.DateField('Start date')
    end_date = models.DateField('End date')
    season_round = models.IntegerField()
    is_draft = models.BooleanField(
        default=False,
        help_text="If enabled, this season is a draft and not yet published."
    )

    class Meta:
        ordering = ['-start_date',]

    def __str__(self):
        return str(self.start_date.year) + ' Round ' + str(self.season_round)

    def get_stats(self):
        """
        Generates the season stats
        """
        # Get aggregated counts directly from related tables
        player_count = League.objects.filter(ladder__season=self).count()
        results_count = Result.objects.filter(ladder__season=self).count() / 2

        # Calculate total possible games by iterating through ladders
        # but get league counts efficiently
        ladder_league_counts = self.ladder_set.annotate(
            league_count=models.Count('league')
        ).values_list('league_count', flat=True)

        total_games_count = 0.0
        for league_count in ladder_league_counts:
            total_games_count += (league_count * (league_count - 1)) / 2

        # Avoid division by zero
        percentage_played = (results_count / total_games_count) * 100 if total_games_count > 0 else 0

        return {
            'divisions': self.ladder_set.count(),
            'percentage_played': "{0:.2f}".format(percentage_played),
            'total_games_count': total_games_count,
            'results_count': results_count,
            'player_count': player_count
        }

    def get_leader_stats(self, user):
        """
        Generates the list of leaders for current season
        """
        current_leaders = {}

        # Prefetch related data to avoid N+1 queries
        ladders = self.ladder_set.prefetch_related('league_set__player')

        for ladder in ladders:
            current_leaders[ladder.id] = ladder.get_leader(user=user)

        return {
            'current_leaders': current_leaders,
        }

    def get_progress(self):
        """
        Query how many games have been played so far.
        Returns all the existing fields plus:
          - season_start (YYYY-MM-DD)
          - today_day (int, clamped to [0, season_length])
        """
        # Daily result counts
        daily_results = (
            Result.objects
            .filter(ladder__season=self)
            .annotate(date_only=TruncDate('date_added'))
            .values('date_only')
            .annotate(added_count=Count('id'))
            .order_by('date_only')
        )

        # Player counts per ladder
        ladder_player_counts = (
            self.ladder_set
            .annotate(player_count=Count('league'))
            .values_list('player_count', flat=True)
        )

        # Process results
        played = []
        played_days = []
        played_cumulative = []
        played_cumulative_count = 0
        latest_result = None

        for r in daily_results:
            date_added = r['date_only']
            added_count = r['added_count']

            played.append(int(added_count))
            played_days.append((date_added - self.start_date).days)

            # Each match creates 2 results -> use integer division
            played_cumulative_count += (added_count // 2)
            played_cumulative.append(int(played_cumulative_count))
            latest_result = date_added

        # Total possible matches across ladders: nC2 per ladder
        total_matches = sum(
            (pc - 1) * pc // 2
            for pc in ladder_player_counts
        )

        season_length = (self.end_date - self.start_date).days
        # Compute "today" relative to start; clamp to chart domain
        today_idx = (now().date() - self.start_date).days
        today_idx = max(0, min(today_idx, season_length))

        return {
            "season_days": [0, season_length],
            "season_total_matches": [0, int(total_matches)],
            "played_days": played_days,
            "played": played,
            "played_cumulative": played_cumulative,
            "latest_result": latest_result.strftime("%B %d, %Y") if latest_result else "-",
            "season_start": self.start_date.isoformat(),  # "YYYY-MM-DD"
            "today_day": today_idx,
        }


class Player(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, blank=True)
    is_authed = False

    def __str__(self):
        return self.full_name(authenticated=self.is_authed)

    def full_name(self, authenticated = False):
        string = self.first_name
        if self.last_name:
            last_names = self.last_name.split()
            if not authenticated:
                last_names[-1] = last_names[-1][:1].capitalize() + '.'  # abbreviate last name
            string += ' ' + ' '.join(last_names)

        return string

    def player_stats(self):
        """
        Calculates stats about the players historical performance.
        """
        played = self.result_player.count()
        won = float(self.result_player.filter(result=9).count())
        lost = played - won  # more efficient than doing a count on the object

        # safe division (not by 0)
        if played != 0:
            win_rate = won / float(played) * 100.00
            # 2 points for winning, 1 for playing
            additional_points = ((won * 2) + played) / played
        else:
            return {
                'played': "-",
                'win_rate': "- %",
                'average': "-"
            }

        # work out the average with additional points
        average = list(self.result_player.aggregate(Avg('result')).values())[0]
        average_with_additional = average + additional_points

        leagues = self.league_set.filter(player=self)

        match_count = 0
        for league in leagues:
            # count other players in ladder minus the player to get games
            match_count += league.ladder.league_set.count() - 1

        completion_rate = float(played) / float(match_count) * 100.00

        return {
            'played': played,
            'win_rate': "{0:.2f} %".format(win_rate),
            'completion_rate': "{0:.2f} %".format(completion_rate),
            'average': "{0:.2f}".format(average_with_additional)
        }


class Ladder(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    division = models.IntegerField()
    ladder_type = models.CharField(max_length=100)

    def __str__(self):
        return str(self.season.start_date.year) + ' Round ' + str(self.season.season_round) + ' - Division: ' + str(
            self.division)

    def is_closed(self):
        """
        Is the ladder finished
        """
        return date.today() > self.season.end_date

    def get_leader(self, user):
        """
        Finds the leader of the ladder
        """
        from collections import defaultdict

        # Use defaultdict to avoid KeyError handling
        totals = defaultdict(int)

        # Get results with player data in one query
        results = self.result_set.select_related('player').filter(ladder=self)

        for result in results:
            if result.result == 9:
                totals[result.player] += int(result.result) + 3
            else:
                totals[result.player] += int(result.result) + 1

        url = reverse('ladder', kwargs={
            'year': self.season.start_date.year,
            'season_round': self.season.season_round,
            'division_id': self.division
        })

        if not totals:
            return {
                'player': 'No Results',
                'player_id': '../#',
                'total': '-',
                'division': self.division,
                'url': url,
                'played': 0
            }

        # Find the leader
        player = max(totals.items(), key=lambda x: x[1])[0]

        # Calculate percentage played more efficiently
        league_count = self.league_set.count()
        if league_count > 1:
            total_matches = league_count * (league_count - 1) / 2
            matches_played = self.result_set.count() / 2
            perc_matches_played = (matches_played / total_matches) * 100 if total_matches > 0 else 0
        else:
            perc_matches_played = 0

        return {
            'player': player.full_name(authenticated=user.is_authenticated),
            'player_id': player.id,
            'total': totals[player],
            'division': self.division,
            'url': url,
            'played': round(perc_matches_played, 2)
        }

    def get_latest_results(self):
        """
        Gets latest results for the ladder
        """
        results = {}
        for result in self.result_set.filter(ladder=self).order_by('-date_added')[:10]:  # [:10] to limit to 5

            try:
                opponent = self.result_set.filter(ladder=self, player=result.opponent, opponent=result.player)[0]
            except IndexError:
                continue  # this exception happens if result does not have opponent
            player_opponent_index = ''.join(str(e) for e in sorted([result.player.id, opponent.player.id]))
            try:
                if results[player_opponent_index]:
                    continue
            except KeyError:
                results[player_opponent_index] = {'player': result.player, 'player_result': result.result,
                                                  'opponent_result': opponent.result, 'opponent': opponent.player,
                                                  'date_added': result.date_added}

        ordered_results = {}
        i = 0
        for key in sorted(results, key=lambda x: (results[x]['date_added']), reverse=True):
            ordered_results[i] = results[key]
            i += 1

        return list(ordered_results.items())

    def get_email_latest(self, days: int = 1, limit: int = 5):
        """
        Return two buckets for the email:
          - 'new': all new results in the last `days` (deduped by pair, newest first)
          - 'recent': the next `limit` recent results (deduped) excluding those already in 'new'
        Structure of each item matches get_latest_results():
        {'player', 'player_result', 'opponent_result', 'opponent', 'date_added'}
        """
        since = now().date() - datetime.timedelta(days=days)

        # Helper to build the pairwise, deduped list with optional date filter
        def _collect(filter_since=None, exclude_keys=None, max_items=None):
            exclude_keys = exclude_keys or set()
            out = {}
            qs = self.result_set.filter(ladder=self)
            if filter_since is not None:
                qs = qs.filter(date_added__gte=filter_since)
            qs = qs.order_by('-date_added')

            for result in qs:
                try:
                    opponent = self.result_set.filter(
                        ladder=self, player=result.opponent, opponent=result.player
                    )[0]
                except IndexError:
                    continue  # skip incomplete pairs

                pair_key = ''.join(str(e) for e in sorted([result.player_id, opponent.player_id]))
                if pair_key in exclude_keys or pair_key in out:
                    continue

                out[pair_key] = {
                    'player': result.player,
                    'player_result': result.result,
                    'opponent_result': opponent.result,
                    'opponent': opponent.player,
                    'date_added': result.date_added,
                }

                if max_items is not None and len(out) >= max_items:
                    break

            # order newest first
            ordered = sorted(out.values(), key=lambda x: x['date_added'], reverse=True)
            return ordered, set(out.keys())

        # (1) Everything new in the past `days`
        new_list, new_keys = _collect(filter_since=since)

        # (2) Next N recent excluding the above
        recent_list, _ = _collect(filter_since=None, exclude_keys=new_keys, max_items=limit)

        return {'new': new_list, 'recent': recent_list}

    def get_stats(self):
        """
        Generates the stats for current division
        """
        total_matches_played = 0.00
        total_matches = self.league_set.count() * (self.league_set.count() - 1) / 2
        total_matches_played += self.result_set.count() / 2
        perc_matches_played = (total_matches_played / total_matches) * 100

        return {
            'total_matches_played': int(total_matches_played),
            'total_matches': int(total_matches),
            'perc_matches_played': perc_matches_played
        }

class LadderSubscription(models.Model):
    ladder = models.ForeignKey(Ladder, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscribed_at = models.DateField()
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return self.user.email

class League(models.Model):
    ladder = models.ForeignKey(Ladder, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    sort_order = models.IntegerField(default=0)

    class Meta(object):
        ordering = ['sort_order']

    def __str__(self):
        return self.player.first_name + ' ' + self.player.last_name

    def player_stats(self):
        """
        Generates the player stats for player listings - Optimized to use prefetched data
        """
        # Get all results for this player in this ladder
        # This should use prefetched data from 'player__result_player'
        results = [r for r in self.player.result_player.all() if r.ladder_id == self.ladder.id]

        if not results:
            return {
                'total_points': 0,
                'games': 0,
                'pointsdivgames': 0,
                'won_count': 0,
                'percplayed': 0
            }

        total_points = 0.0
        games = len(results)
        won_count = 0

        for result in results:
            if result.result == 9:
                total_points += (result.result + 2 + 1)  # two for winning one for playing
                won_count += 1
            else:
                total_points += (result.result + 1)  # one for playing

        # Calculate stats
        pointsdivgames = total_points / games if games > 0 else 0

        # Use prefetched league_set instead of .count() which always hits DB
        league_count = len(self.ladder.league_set.all())  # Uses prefetched data
        percplayed = games / (league_count - 1) * 100 if league_count > 1 else 0

        return {
            'total_points': total_points,
            'games': games,
            'pointsdivgames': pointsdivgames,
            'won_count': won_count,
            'percplayed': percplayed
        }


class Result(models.Model):
    ladder = models.ForeignKey(Ladder, on_delete=models.CASCADE)
    player = models.ForeignKey(Player,on_delete=models.CASCADE, related_name='result_player')
    opponent = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='result_opponent')
    result = models.IntegerField()
    date_added = models.DateField('Date added')
    inaccurate_flag = models.BooleanField(default=None)
    entered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='entered_results')

    def __str__(self):
        return (self.player.first_name + ' ' + self.player.last_name) + ' vs ' + (
            self.opponent.first_name + ' ' + self.opponent.last_name) + (' score: ' + str(self.result))

@receiver(post_save, sender=League)
def auto_subscribe_on_league_create(sender, instance: League, created, **kwargs):
    if not created:
        return
    player = instance.player
    # only if the player has a linked user
    if getattr(player, "user_id", None):
        LadderSubscription.objects.get_or_create(
            ladder=instance.ladder,
            user=player.user,
            defaults={'subscribed_at': datetime.date.today()}
        )

class Prospect(models.Model):
    class Status(models.TextChoices):
        NEW       = "new",       "New"
        CONTACTED = "contacted", "Contacted"
        READY     = "ready",     "Ready"
        ADDED     = "added",     "Added to draft"
        REJECTED  = "rejected",  "Rejected"

    first_name   = models.CharField(max_length=80)
    last_name    = models.CharField(max_length=80)
    email        = models.EmailField(unique=True)
    ability_note = models.CharField(max_length=200, blank=True)
    status       = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.last_name}, {self.first_name} <{self.email}>"

class DraftRemoval(models.Model):
    season        = models.ForeignKey("Season", on_delete=models.CASCADE, related_name="draft_removals")
    player        = models.ForeignKey("Player", on_delete=models.CASCADE)
    from_division = models.PositiveIntegerField()
    note          = models.CharField(max_length=200, blank=True)
    removed_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-removed_at",)
        indexes = [models.Index(fields=["season", "from_division"])]

    def __str__(self):
        return f"{self.player} from {self.season.name} division {self.from_division}"

