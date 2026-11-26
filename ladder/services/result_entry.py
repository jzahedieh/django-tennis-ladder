import datetime

from django.db import transaction
from django.db.models import Q

from ladder.models import Ladder, League, Player, Result


class ResultMutationError(Exception):
    """Domain validation error raised during match result mutations."""

    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ResultPermissionError(ResultMutationError):
    """Permission error raised when a user cannot mutate a match result."""

    status_code = 403


class ResultNotFoundError(ResultMutationError):
    """Lookup error raised when a player, division, or match pair does not exist."""

    status_code = 404


class ResultMutationService:
    """
    Shared service for reading player result-entry context and performing
    atomic, validated match result creation, editing, and deletion.
    """

    @classmethod
    def get_active_ladder_for_user(cls, user) -> tuple[Player, Ladder]:
        me = Player.objects.filter(user=user).first()
        if me is None:
            raise ResultNotFoundError("No player profile linked to this account.")

        ladder = (
            Ladder.objects.filter(league__player=me, season__is_draft=False)
            .select_related("season")
            .order_by("-season__start_date", "-season__season_round", "-id")
            .first()
        )
        if ladder is None:
            raise ResultNotFoundError("No active ladder division found for this player.")

        return me, ladder

    @classmethod
    def get_unplayed_opponents(cls, player: Player, ladder: Ladder) -> list[Player]:
        league_players = [
            lg.player for lg in ladder.league_set.select_related("player").all()
        ]
        played_pairs = set()
        for r in Result.objects.filter(ladder=ladder).values_list("player_id", "opponent_id"):
            played_pairs.add(tuple(sorted(r)))

        unplayed = []
        for opp in league_players:
            if opp.id == player.id:
                continue
            if tuple(sorted((player.id, opp.id))) not in played_pairs:
                unplayed.append(opp)
        return unplayed

    @classmethod
    def get_entered_matches(cls, player: Player, ladder: Ladder) -> list[dict]:
        entered_raw = (
            Result.objects.filter(ladder=ladder)
            .filter(Q(player=player) | Q(opponent=player))
            .select_related("player", "opponent", "entered_by")
            .order_by("-date_added", "-id")
        )

        pairs = {}
        for r in entered_raw:
            key = tuple(sorted((r.player_id, r.opponent_id)))
            pairs.setdefault(key, []).append(r)

        entered = []
        for (a_id, b_id), rows in pairs.items():
            if len(rows) == 1:
                r = rows[0]
                try:
                    mirror = Result.objects.select_related(
                        "player", "opponent", "entered_by"
                    ).get(
                        ladder=ladder,
                        player_id=r.opponent_id,
                        opponent_id=r.player_id,
                    )
                    rows = [r, mirror]
                except Result.DoesNotExist:
                    continue

            ra, rb = rows[0], rows[1]
            my_row = ra if ra.player_id == player.id else rb
            opp_row = rb if ra.player_id == player.id else ra
            reason = my_row.incomplete_reason or opp_row.incomplete_reason

            is_incomplete_time = (
                (my_row.result < 9 and opp_row.result < 9)
                or reason == Result.IncompleteReason.TIME
            )
            is_injury = (
                reason == Result.IncompleteReason.INJURY
                and (my_row.result == 9 or opp_row.result == 9)
            )

            if is_incomplete_time:
                winner_row, loser_row = my_row, opp_row
                outcome_code = "I"
                score_display = f"{my_row.result}\u2013{opp_row.result} (Inc.)"
            else:
                if ra.result == 9:
                    winner_row, loser_row = ra, rb
                elif rb.result == 9:
                    winner_row, loser_row = rb, ra
                else:
                    winner_row, loser_row = my_row, opp_row

                if my_row.result == 9:
                    outcome_code = "W"
                    score_display = (
                        f"9\u2013{opp_row.result} (Ret.)"
                        if is_injury
                        else f"9\u2013{opp_row.result}"
                    )
                else:
                    outcome_code = "R" if is_injury else "L"
                    score_display = (
                        f"{my_row.result}\u20139 (Ret.)"
                        if is_injury
                        else f"{my_row.result}\u20139"
                    )

            entered.append(
                {
                    "winner": winner_row.player,
                    "loser": loser_row.player,
                    "losing_score": loser_row.result,
                    "opponent": opp_row.player,
                    "my_score": my_row.result,
                    "opp_score": opp_row.result,
                    "outcome_code": outcome_code,
                    "is_incomplete": is_incomplete_time,
                    "is_injury": is_injury,
                    "incomplete_reason": reason
                    or (Result.IncompleteReason.TIME if is_incomplete_time else None),
                    "score_display": score_display,
                    "date_added": winner_row.date_added,
                    "entered_by": winner_row.entered_by or loser_row.entered_by,
                    "pair_key": f"{a_id}-{b_id}",
                }
            )

        return entered

    @classmethod
    def can_edit_match(cls, user, ladder: Ladder, player_a_id: int, player_b_id: int) -> bool:
        if user.is_superuser:
            return True
        return Player.objects.filter(
            user=user, id__in=(player_a_id, player_b_id)
        ).exists()

    @staticmethod
    def parse_pair_key(pair_key: str) -> tuple[int, int]:
        parts = pair_key.split("-")
        if len(parts) != 2:
            raise ResultNotFoundError("Invalid match pair key.")
        try:
            a_id, b_id = int(parts[0]), int(parts[1])
        except ValueError as exc:
            raise ResultNotFoundError("Invalid match pair key.") from exc
        if a_id <= 0 or b_id <= 0 or a_id == b_id:
            raise ResultNotFoundError("Invalid match pair key.")
        return a_id, b_id

    @classmethod
    def get_match_pair(cls, pair_key: str, viewer_player: Player | None = None) -> dict:
        a_id, b_id = cls.parse_pair_key(pair_key)

        r_ab = (
            Result.objects.select_related("player", "ladder", "ladder__season")
            .filter(player_id=a_id, opponent_id=b_id, ladder__season__is_draft=False)
            .order_by("-ladder__season__start_date", "-ladder__season__season_round", "-id")
            .first()
        )
        if r_ab is None:
            raise ResultNotFoundError("Match result not found.")

        ladder = r_ab.ladder
        try:
            r_ba = Result.objects.select_related("player").get(
                ladder=ladder, player_id=b_id, opponent_id=a_id
            )
        except Result.DoesNotExist as exc:
            raise ResultNotFoundError("Match result not found.") from exc

        reason = r_ab.incomplete_reason or r_ba.incomplete_reason
        is_incomplete_time = (
            (r_ab.result < 9 and r_ba.result < 9)
            or reason == Result.IncompleteReason.TIME
        )
        is_injury = (
            reason == Result.IncompleteReason.INJURY
            and (r_ab.result == 9 or r_ba.result == 9)
        )

        if is_incomplete_time:
            if viewer_player and viewer_player.id == b_id:
                winner, loser = r_ba.player, r_ab.player
                winner_score, losing_score = r_ba.result, r_ab.result
            else:
                winner, loser = r_ab.player, r_ba.player
                winner_score, losing_score = r_ab.result, r_ba.result
            match_mode = "time"
        else:
            if r_ab.result == 9:
                winner, loser, winner_score, losing_score = (
                    r_ab.player,
                    r_ba.player,
                    9,
                    r_ba.result,
                )
            else:
                winner, loser, winner_score, losing_score = (
                    r_ba.player,
                    r_ab.player,
                    9,
                    r_ab.result,
                )
            match_mode = "injury" if is_injury else "completed"

        return {
            "a_id": a_id,
            "b_id": b_id,
            "ladder": ladder,
            "r_ab": r_ab,
            "r_ba": r_ba,
            "winner": winner,
            "loser": loser,
            "winner_score": winner_score,
            "losing_score": losing_score,
            "match_mode": match_mode,
            "is_incomplete": is_incomplete_time,
            "is_injury": is_injury,
            "reason": reason,
            "pair_key": f"{min(a_id, b_id)}-{max(a_id, b_id)}",
        }

    @classmethod
    def _validate_score(cls, score: int | None, label: str = "Score") -> int:
        if score is None or not (0 <= score <= 8):
            raise ResultMutationError(f"{label} must be between 0 and 8.")
        return int(score)

    @classmethod
    def submit_result(
        cls,
        user,
        ladder: Ladder,
        opponent_id: int,
        outcome: str,
        primary_score: int,
        opponent_score: int | None = None,
        incomplete_reason: str | None = None,
        injured_player: str | None = None,
        enforce_open: bool = True,
    ) -> dict:
        me = Player.objects.filter(user=user).first()
        if me is None or not League.objects.filter(ladder=ladder, player=me).exists():
            raise ResultPermissionError("You are not a member of this division.")

        if enforce_open and ladder.is_closed() and not user.is_superuser:
            raise ResultMutationError("This ladder round is now closed.")

        opp = Player.objects.filter(pk=opponent_id, league__ladder=ladder).first()
        if opp is None or opp.id == me.id:
            raise ResultMutationError("Invalid opponent for this division.")

        score = cls._validate_score(primary_score, label="Score")

        if outcome not in ("won", "lost", "incomplete"):
            raise ResultMutationError("Invalid match outcome.")

        reason = None
        if outcome == "won":
            my_score = 9
            opp_score = score
        elif outcome == "lost":
            my_score = score
            opp_score = 9
        else:
            if incomplete_reason not in (
                Result.IncompleteReason.TIME,
                Result.IncompleteReason.INJURY,
            ):
                raise ResultMutationError("Please select a reason for the incomplete match.")
            reason = incomplete_reason
            if reason == Result.IncompleteReason.TIME:
                opp_score = cls._validate_score(
                    opponent_score, label="Opponent's score"
                )
                my_score = score
            else:
                if injured_player not in ("opponent", "me"):
                    raise ResultMutationError("Please select who retired due to injury.")
                if injured_player == "opponent":
                    my_score = 9
                    opp_score = score
                else:
                    my_score = score
                    opp_score = 9

        now_dt = datetime.datetime.now()
        with transaction.atomic():
            Result.objects.filter(ladder=ladder, player=me, opponent=opp).delete()
            Result.objects.filter(ladder=ladder, player=opp, opponent=me).delete()

            Result.objects.create(
                ladder=ladder,
                player=me,
                opponent=opp,
                result=my_score,
                date_added=now_dt,
                incomplete_reason=reason,
                entered_by=user,
            )
            Result.objects.create(
                ladder=ladder,
                player=opp,
                opponent=me,
                result=opp_score,
                date_added=now_dt,
                incomplete_reason=reason,
                entered_by=user,
            )

        return {
            "pair_key": f"{min(me.id, opp.id)}-{max(me.id, opp.id)}",
            "ladder": ladder,
            "my_score": my_score,
            "opp_score": opp_score,
            "incomplete_reason": reason,
        }

    @classmethod
    def edit_result(
        cls,
        user,
        pair_key: str,
        match_mode: str,
        winner_id: int | None = None,
        winner_score: int | None = None,
        losing_score: int | None = None,
        enforce_open: bool = True,
    ) -> tuple[Ladder, bool]:
        me = Player.objects.filter(user=user).first()
        info = cls.get_match_pair(pair_key, viewer_player=me)
        ladder = info["ladder"]
        a_id = info["a_id"]
        b_id = info["b_id"]

        if not cls.can_edit_match(user, ladder, a_id, b_id):
            raise ResultPermissionError("You do not have permission to edit this result.")

        if enforce_open and ladder.is_closed() and not user.is_superuser:
            raise ResultMutationError("This ladder round is now closed.")

        if match_mode not in ("completed", "time", "injury"):
            raise ResultMutationError("Invalid match mode.")

        if match_mode == "time":
            score_w = cls._validate_score(winner_score, label="Your score")
            score_l = cls._validate_score(losing_score, label="Opponent score")
            if (
                info["match_mode"] == "time"
                and score_w == info["winner_score"]
                and score_l == info["losing_score"]
            ):
                return ladder, False

            now_dt = datetime.datetime.now()
            with transaction.atomic():
                Result.objects.filter(ladder=ladder, player_id=a_id, opponent_id=b_id).delete()
                Result.objects.filter(ladder=ladder, player_id=b_id, opponent_id=a_id).delete()
                Result.objects.create(
                    ladder=ladder,
                    player_id=info["winner"].id,
                    opponent_id=info["loser"].id,
                    result=score_w,
                    incomplete_reason=Result.IncompleteReason.TIME,
                    date_added=now_dt,
                    entered_by=user,
                )
                Result.objects.create(
                    ladder=ladder,
                    player_id=info["loser"].id,
                    opponent_id=info["winner"].id,
                    result=score_l,
                    incomplete_reason=Result.IncompleteReason.TIME,
                    date_added=now_dt,
                    entered_by=user,
                )
            return ladder, True

        if winner_id not in (a_id, b_id):
            raise ResultMutationError("Winner must be one of the two match players.")

        new_losing_score = cls._validate_score(losing_score, label="Losing score")
        new_reason = (
            Result.IncompleteReason.INJURY if match_mode == "injury" else None
        )

        if (
            match_mode == info["match_mode"]
            and winner_id == info["winner"].id
            and new_losing_score == info["losing_score"]
        ):
            return ladder, False

        win_id, lose_id = (a_id, b_id) if winner_id == a_id else (b_id, a_id)
        now_dt = datetime.datetime.now()
        with transaction.atomic():
            Result.objects.filter(ladder=ladder, player_id=a_id, opponent_id=b_id).delete()
            Result.objects.filter(ladder=ladder, player_id=b_id, opponent_id=a_id).delete()
            Result.objects.create(
                ladder=ladder,
                player_id=win_id,
                opponent_id=lose_id,
                incomplete_reason=new_reason,
                result=9,
                date_added=now_dt,
                entered_by=user,
            )
            Result.objects.create(
                ladder=ladder,
                player_id=lose_id,
                opponent_id=win_id,
                incomplete_reason=new_reason,
                result=new_losing_score,
                date_added=now_dt,
                entered_by=user,
            )

        return ladder, True

    @classmethod
    def delete_result(cls, user, pair_key: str, enforce_open: bool = True) -> Ladder:
        info = cls.get_match_pair(pair_key)
        ladder = info["ladder"]
        a_id = info["a_id"]
        b_id = info["b_id"]

        if not cls.can_edit_match(user, ladder, a_id, b_id):
            raise ResultPermissionError("You do not have permission to delete this result.")

        if enforce_open and ladder.is_closed() and not user.is_superuser:
            raise ResultMutationError("This ladder round is now closed.")

        with transaction.atomic():
            Result.objects.filter(ladder=ladder, player_id=a_id, opponent_id=b_id).delete()
            Result.objects.filter(ladder=ladder, player_id=b_id, opponent_id=a_id).delete()

        return ladder

    @classmethod
    def admin_submit_result(
        cls,
        user,
        ladder: Ladder,
        winner_id: int,
        loser_id: int,
        losing_score: int,
        incomplete_reason: str | None = None,
    ) -> dict:
        if not user.is_superuser:
            raise ResultPermissionError("Superuser permissions required.")

        if winner_id == loser_id:
            raise ResultMutationError("Winner and loser cannot be the same player.")

        division_player_ids = set(
            League.objects.filter(
                ladder=ladder, player_id__in=(winner_id, loser_id)
            ).values_list("player_id", flat=True)
        )
        if winner_id not in division_player_ids or loser_id not in division_player_ids:
            raise ResultMutationError("Both players must belong to this division.")

        score = cls._validate_score(losing_score, label="Losing score")

        reason = incomplete_reason or None
        if reason not in (
            None,
            Result.IncompleteReason.TIME,
            Result.IncompleteReason.INJURY,
        ):
            raise ResultMutationError("Invalid incomplete reason.")

        now_dt = datetime.datetime.now()
        with transaction.atomic():
            Result.objects.filter(
                ladder=ladder, player_id=loser_id, opponent_id=winner_id
            ).delete()
            Result.objects.filter(
                ladder=ladder, player_id=winner_id, opponent_id=loser_id
            ).delete()

            Result.objects.create(
                ladder=ladder,
                player_id=loser_id,
                opponent_id=winner_id,
                result=score,
                date_added=now_dt,
                incomplete_reason=reason,
                entered_by=user,
            )
            Result.objects.create(
                ladder=ladder,
                player_id=winner_id,
                opponent_id=loser_id,
                result=9,
                date_added=now_dt,
                incomplete_reason=reason,
                entered_by=user,
            )

        return {
            "pair_key": f"{min(winner_id, loser_id)}-{max(winner_id, loser_id)}",
            "ladder": ladder,
        }
