from datetime import date

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Case, When, Value, FloatField, F, Sum, Count
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from ladder.models import Season, Player, Ladder, Result, League, LadderSubscription, Prospect


# ------------------------------
# Shared helpers for draft admin
# ------------------------------
class DraftHelpers:
    """Utility methods used by SeasonAdmin's draft workspace."""

    # --- redirects / urls ---

    def _to_workspace(self, season, fragment: str = ""):
        """Redirect back to draft workspace, optionally to an anchor."""
        url = reverse("admin:ladder_season_draft", args=[season.id])
        return redirect(f"{url}{fragment}")

    # --- lookups / state ---

    def _previous_season(self, season: Season):
        return (
            Season.objects.filter(start_date__lt=season.start_date)
            .order_by("-start_date")
            .first()
        )

    def _get_ladder(self, season: Season, division: int):
        return Ladder.objects.filter(season=season, division=division).first()

    def _last_league_for_player(self, season: Season, player_id: int):
        """
        Player's last league BEFORE this season; tie-break by lowest division.
        """
        return (
            League.objects.filter(
                player_id=player_id,
                ladder__season__start_date__lt=season.start_date,
            )
            .select_related("ladder__season")
            .order_by("-ladder__season__start_date", "ladder__division")
            .first()
        )

    # --- ordering ---

    def _next_sort(self, ladder: Ladder) -> int:
        last = League.objects.filter(ladder=ladder).order_by("-sort_order").first()
        return (last.sort_order + 10) if last else 10

    def _top_sort(self, ladder: Ladder) -> int:
        first = League.objects.filter(ladder=ladder).order_by("sort_order").first()
        return (first.sort_order - 10) if first else 10

    def _renumber_positions(self, ladder: Ladder):
        """Normalize sort_order to 10,20,30… in current visual order."""
        leagues = (
            League.objects.filter(ladder=ladder)
            .order_by("sort_order", "player__last_name", "player__first_name")
        )
        for i, lg in enumerate(leagues, start=1):
            new_val = i * 10
            if lg.sort_order != new_val:
                lg.sort_order = new_val
                lg.save(update_fields=["sort_order"])

    # --- scoring / stats ---

    @property
    def _points_expr(self):
        # Points rule: 9 → 12; else → result + 1 (matches your template logic)
        return Case(
            When(result=9, then=Value(12.0)),
            default=F("result") + Value(1.0),
            output_field=FloatField(),
        )

    def _stats_for(self, player_id: int, season_obj: Season, division: int):
        """
        Totals / average / matches for a player within a specific season+division.
        """
        agg = (
            Result.objects.filter(
                player_id=player_id,
                ladder__season=season_obj,
                ladder__division=division,
            )
            .aggregate(
                total=Coalesce(Sum(self._points_expr), Value(0.0)),
                matches=Coalesce(Count("id"), Value(0)),
            )
        )
        total = float(agg["total"] or 0.0)
        matches = int(agg["matches"] or 0)
        avg = round(total / matches, 2) if matches else 0.0
        return round(total, 2), avg, matches

    # --- subscriptions ---

    def _ensure_subscription(self, ladder: Ladder, player):
        """Create subscription if the player has a linked user."""
        if getattr(player, "user_id", None):
            LadderSubscription.objects.get_or_create(
                ladder=ladder, user=player.user, defaults={"subscribed_at": date.today()}
            )

    def _swap_subscription(self, old_ladder: Ladder, new_ladder: Ladder, player):
        """Subscribe to new ladder and drop the old subscription."""
        if getattr(player, "user_id", None):
            LadderSubscription.objects.get_or_create(
                ladder=new_ladder,
                user=player.user,
                defaults={"subscribed_at": date.today()},
            )
            LadderSubscription.objects.filter(
                ladder=old_ladder, user=player.user
            ).delete()


# ------------------------------
# Season admin (draft workspace)
# ------------------------------
@admin.register(Season)
class SeasonAdmin(DraftHelpers, admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "season_round", "is_draft")
    list_filter = ("is_draft", "season_round")
    date_hierarchy = "start_date"
    fields = ("name", "start_date", "end_date", "season_round", "is_draft")
    change_form_template = "admin/ladder/season/change_form_with_workspace_link.html"

    # --- urls ---

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:season_id>/draft/",
                self.admin_site.admin_view(self.draft_workspace),
                name="ladder_season_draft",
            ),
            path(
                "<int:season_id>/draft/populate/",
                self.admin_site.admin_view(self.populate_from_previous),
                name="ladder_season_populate",
            ),
            path(
                "<int:season_id>/draft/add_division/",
                self.admin_site.admin_view(self.add_division),
                name="ladder_season_add_div",
            ),
            path(
                "<int:season_id>/draft/delete_division/<int:division>/",
                self.admin_site.admin_view(self.delete_division),
                name="ladder_season_del_div",
            ),
            # row actions
            path(
                "<int:season_id>/draft/<int:division>/add/",
                self.admin_site.admin_view(self.add_player),
                name="ladder_season_add_player",
            ),
            path(
                "<int:season_id>/draft/<int:division>/remove/<int:league_id>/",
                self.admin_site.admin_view(self.remove_player),
                name="ladder_season_remove",
            ),
            path(
                "<int:season_id>/draft/<int:division>/promote/<int:league_id>/",
                self.admin_site.admin_view(self.promote),
                name="ladder_season_promote",
            ),
            path(
                "<int:season_id>/draft/<int:division>/demote/<int:league_id>/",
                self.admin_site.admin_view(self.demote),
                name="ladder_season_demote",
            ),
            path(
                "<int:season_id>/draft/<int:division>/move_up/<int:league_id>/",
                self.admin_site.admin_view(self.move_up),
                name="ladder_season_move_up",
            ),
            path(
                "<int:season_id>/draft/<int:division>/move_down/<int:league_id>/",
                self.admin_site.admin_view(self.move_down),
                name="ladder_season_move_down",
            ),
            path(
                "<int:season_id>/draft/<int:division>/invite_prospect/",
                self.admin_site.admin_view(self.invite_prospect),
                name="ladder_season_invite_prospect",
            ),
        ]
        return custom + urls

    # --- populate from previous ---

    @transaction.atomic
    def populate_from_previous(self, request, season_id: int):
        season = get_object_or_404(Season, pk=season_id)
        if request.method != "POST":
            return self._to_workspace(season)

        prev = self._previous_season(season)
        if not prev:
            messages.error(request, "No previous season found to copy from.")
            return self._to_workspace(season)

        if League.objects.filter(ladder__season=season).exists():
            messages.warning(request, "This draft already has players. (Nothing changed.)")
            return self._to_workspace(season)

        created_ladders = 0
        created_leagues = 0

        for old_ladder in Ladder.objects.filter(season=prev).order_by("division"):
            player_ids = list(
                League.objects.filter(ladder=old_ladder).values_list("player_id", flat=True)
            )
            if not player_ids:
                continue

            # totals for that exact division in the previous season
            stats = (
                Result.objects.filter(ladder=old_ladder, player_id__in=player_ids)
                .values("player_id")
                .annotate(total=Coalesce(Sum(self._points_expr), Value(0.0)))
            )
            totals = {s["player_id"]: float(s["total"]) for s in stats}
            players = list(Player.objects.filter(id__in=player_ids))

            def name_key(p):
                first = (p.first_name or "").strip().lower()
                last = (p.last_name or "").strip().lower()
                return f"{last} {first}"

            players_sorted = sorted(
                players, key=lambda p: (-totals.get(p.id, 0.0), name_key(p))
            )

            new_ladder, made_ladder = Ladder.objects.get_or_create(
                season=season, division=old_ladder.division
            )
            if made_ladder:
                created_ladders += 1

            for idx, p in enumerate(players_sorted, start=1):
                _, made = League.objects.get_or_create(
                    ladder=new_ladder, player=p, defaults={"sort_order": idx * 10}
                )
                if made:
                    created_leagues += 1

        messages.success(
            request,
            f"Populated from {prev.name}: {created_ladders} division(s), {created_leagues} player rows (sorted by previous total).",
        )
        return self._to_workspace(season)

    # --- workspace view ---

    def draft_workspace(self, request, season_id: int):
        """Tables for the draft season, with live 'last ladder' context."""
        season = get_object_or_404(Season, pk=season_id)
        ladders = (
            Ladder.objects.filter(season=season)
            .order_by("division")
            .prefetch_related("league_set__player")
        )

        divisions = []
        for ladder in ladders:
            rows = []
            leagues = sorted(
                ladder.league_set.all(),
                key=lambda L: (
                    L.sort_order,
                    L.player.last_name or "",
                    L.player.first_name or "",
                ),
            )
            for pos, lg in enumerate(leagues, start=1):
                player = lg.player
                previous = self._last_league_for_player(season, player.id)
                if previous:
                    prev_season = previous.ladder.season
                    prev_div = previous.ladder.division
                    total, avg, played = self._stats_for(player.id, prev_season, prev_div)
                    prev_title = f"{prev_season.name}: Division {prev_div}"
                else:
                    prev_title, total, avg, played = "—", 0.0, 0.0, 0

                name = f"{(player.first_name or '').strip()} {(player.last_name or '').strip()}".strip() or "—"
                rows.append(
                    {
                        "league_id": lg.id,
                        "position": pos,
                        "name": name,
                        "prev_title": prev_title,
                        "total": total,
                        "avg": avg,
                        "played": played,
                    }
                )

            divisions.append({"division": ladder.division, "rows": rows})

        assigned_ids = set(
            League.objects.filter(ladder__season=season).values_list("player_id", flat=True)
        )
        candidates = (
            Player.objects.exclude(id__in=assigned_ids)
            .order_by("last_name", "first_name")
            .values("id", "first_name", "last_name")
        )
        prospects = (
            Prospect.objects
            .exclude(status__in=[Prospect.Status.REJECTED, Prospect.Status.ADDED])
            .order_by("last_name", "first_name")
            .values("id", "first_name", "last_name", "email", "ability_note", "status")
        )

        context = {
            **self.admin_site.each_context(request),
            "season": season,
            "divisions": divisions,
            "candidates": list(candidates),
            "prospects": list(prospects),
        }
        return TemplateResponse(
            request, "admin/ladder/season/draft_workspace.html", context
        )

    # --- division add/delete ---

    def add_division(self, request, season_id: int):
        season = get_object_or_404(Season, pk=season_id)
        if request.method != "POST":
            return self._to_workspace(season)
        last = Ladder.objects.filter(season=season).order_by("-division").first()
        next_div = (last.division + 1) if last else 1
        Ladder.objects.create(season=season, division=next_div)
        messages.success(request, f"Added Division {next_div}.")
        return self._to_workspace(season)

    def delete_division(self, request, season_id: int, division: int):
        season = get_object_or_404(Season, pk=season_id)
        if request.method != "POST":
            return self._to_workspace(season)
        ladder = get_object_or_404(Ladder, season=season, division=division)

        if Result.objects.filter(ladder=ladder).exists():
            messages.error(request, f"Cannot delete Division {division}: it has results.")
            return self._to_workspace(season, f"#div-{division}")

        League.objects.filter(ladder=ladder).delete()
        ladder.delete()
        messages.success(request, f"Deleted Division {division}.")
        return self._to_workspace(season)

    # --- player row actions ---

    @transaction.atomic
    def add_player(self, request, season_id: int, division: int):
        season = get_object_or_404(Season, pk=season_id)
        dst = self._get_ladder(season, division)
        if not dst or request.method != "POST":
            return self._to_workspace(season, f"#div-{division}")

        player_id = request.POST.get("player_id")
        if not player_id:
            messages.error(request, "Choose a player.")
            return self._to_workspace(season, f"#div-{division}")

        if League.objects.filter(ladder__season=season, player_id=player_id).exists():
            messages.warning(request, "That player is already assigned to a division in this season.")
            return self._to_workspace(season, f"#div-{division}")

        league = League.objects.create(
            ladder=dst, player_id=player_id, sort_order=self._next_sort(dst)
        )
        self._renumber_positions(dst)
        self._ensure_subscription(dst, league.player)

        messages.success(request, "Player added.")
        return self._to_workspace(season, f"#div-{division}")

    @transaction.atomic
    def remove_player(self, request, season_id: int, division: int, league_id: int):
        season = get_object_or_404(Season, pk=season_id)
        src = self._get_ladder(season, division)
        league = get_object_or_404(League, pk=league_id, ladder=src)

        if getattr(league.player, "user_id", None):
            LadderSubscription.objects.filter(ladder=src, user=league.player.user).delete()

        league.delete()
        self._renumber_positions(src)
        messages.success(request, "Removed from division.")
        return self._to_workspace(season, f"#div-{division}")

    @transaction.atomic
    def promote(self, request, season_id: int, division: int, league_id: int):
        season = get_object_or_404(Season, pk=season_id)
        src = self._get_ladder(season, division)
        league = get_object_or_404(League, pk=league_id, ladder=src)

        target_div = division - 1
        dst = self._get_ladder(season, target_div)
        if not dst:
            messages.error(request, f"Division {target_div} doesn’t exist. Add it first.")
            return self._to_workspace(season, f"#div-{division}")

        league.ladder = dst
        league.sort_order = self._next_sort(dst)  # to bottom
        league.save(update_fields=["ladder", "sort_order"])

        self._renumber_positions(src)
        self._renumber_positions(dst)
        self._swap_subscription(src, dst, league.player)

        messages.success(request, "Promoted.")
        return self._to_workspace(season, f"#div-{target_div}")

    @transaction.atomic
    def demote(self, request, season_id: int, division: int, league_id: int):
        season = get_object_or_404(Season, pk=season_id)
        src = self._get_ladder(season, division)
        league = get_object_or_404(League, pk=league_id, ladder=src)

        target_div = division + 1
        dst = self._get_ladder(season, target_div)
        if not dst:
            messages.error(request, f"Division {target_div} doesn’t exist. Add it first.")
            return self._to_workspace(season, f"#div-{division}")

        league.ladder = dst
        league.sort_order = self._top_sort(dst)  # to top
        league.save(update_fields=["ladder", "sort_order"])

        self._renumber_positions(src)
        self._renumber_positions(dst)
        self._swap_subscription(src, dst, league.player)

        messages.success(request, "Demoted to top of next division.")
        return self._to_workspace(season, f"#div-{target_div}")

    @transaction.atomic
    def move_up(self, request, season_id: int, division: int, league_id: int):
        season = get_object_or_404(Season, pk=season_id)
        ladder = self._get_ladder(season, division)
        if not ladder:
            messages.error(request, f"Division {division} not found.")
            return self._to_workspace(season)

        row = get_object_or_404(League, pk=league_id, ladder=ladder)
        above = (
            League.objects.filter(ladder=ladder, sort_order__lt=row.sort_order)
            .order_by("-sort_order")
            .first()
        )
        if not above:
            messages.info(request, "Already at the top.")
        else:
            row.sort_order, above.sort_order = above.sort_order, row.sort_order
            row.save(update_fields=["sort_order"])
            above.save(update_fields=["sort_order"])
            self._renumber_positions(ladder)
            messages.success(request, "Moved up.")
        return self._to_workspace(season, f"#row-{league_id}")

    @transaction.atomic
    def move_down(self, request, season_id: int, division: int, league_id: int):
        season = get_object_or_404(Season, pk=season_id)
        ladder = self._get_ladder(season, division)
        if not ladder:
            messages.error(request, f"Division {division} not found.")
            return self._to_workspace(season)

        row = get_object_or_404(League, pk=league_id, ladder=ladder)
        below = (
            League.objects.filter(ladder=ladder, sort_order__gt=row.sort_order)
            .order_by("sort_order")
            .first()
        )
        if not below:
            messages.info(request, "Already at the bottom.")
        else:
            row.sort_order, below.sort_order = below.sort_order, row.sort_order
            row.save(update_fields=["sort_order"])
            below.save(update_fields=["sort_order"])
            self._renumber_positions(ladder)
            messages.success(request, "Moved down.")
        return self._to_workspace(season, f"#row-{league_id}")

    @transaction.atomic
    def invite_prospect(self, request, season_id: int, division: int):
        season = get_object_or_404(Season, pk=season_id)
        dst = self._get_ladder(season, division)
        if not dst or request.method != "POST":
            return self._to_workspace(season, f"#div-{division}")

        pid = request.POST.get("prospect_id")
        prospect = get_object_or_404(Prospect, pk=pid)

        # --- guard against duplicate email (case-insensitive) ---
        User = get_user_model()
        existing_user = User.objects.filter(email__iexact=prospect.email).first()
        if existing_user:
            user = existing_user
            # keep names up to date if blank
            changed = False
            if not user.first_name and prospect.first_name:
                user.first_name = prospect.first_name;
                changed = True
            if not user.last_name and prospect.last_name:
                user.last_name = prospect.last_name;
                changed = True
            if changed:
                user.save(update_fields=["first_name", "last_name"])
        else:
            # username = email for simplicity
            user = User.objects.create(
                username=prospect.email.lower(),
                email=prospect.email.lower(),
                first_name=prospect.first_name,
                last_name=prospect.last_name,
                is_active=True,
            )

        # ensure a Player linked to this user
        player = Player.objects.filter(user=user).first()
        if not player:
            player = Player.objects.create(
                first_name=prospect.first_name,
                last_name=prospect.last_name,
                user=user,
            )

        # assign to player group
        player_group, _ = Group.objects.get_or_create(name="player")
        if not user.groups.filter(id=player_group.id).exists():
            user.groups.add(player_group)

        # prevent double-assignments within this season
        already_assigned = League.objects.filter(ladder__season=season, player=player).exists()
        if already_assigned:
            messages.warning(request, "That player is already assigned to a division in this season.")
            return self._to_workspace(season, f"#div-{division}")

        # add to division
        League.objects.create(ladder=dst, player=player, sort_order=self._next_sort(dst))
        self._renumber_positions(dst)

        # auto-subscribe to this ladder (idempotent; make sure NOT NULL for subscribed_at)
        if getattr(player, "user_id", None):
            LadderSubscription.objects.get_or_create(
                ladder=dst, user=player.user,
                defaults={"subscribed_at": date.today()}
            )

        # mark prospect as 'added' so it drops out of the picker
        if prospect.status != "added":
            prospect.status = "added"
            prospect.save(update_fields=["status"])

        messages.success(request, f"Added {player.full_name(authenticated=True)} from prospects.")
        return self._to_workspace(season, f"#div-{division}")


# ------------------------------
# The rest of your admin configs
# ------------------------------
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name")
    search_fields = ("first_name", "last_name")
    ordering = ("last_name",)


@admin.register(Ladder)
class LadderAdmin(admin.ModelAdmin):
    list_filter = ["season"]
    list_display = ("season", "division")
    ordering = ("season", "division")


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_filter = ["ladder__season"]
    list_display = ("player", "ladder", "sort_order")
    search_fields = ("player__first_name", "player__last_name")
    ordering = ("-ladder__season__start_date", "ladder__division", "sort_order")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_filter = ["ladder__season"]
    search_fields = ["player__first_name", "player__last_name"]
    list_display = ("ladder", "player", "opponent", "result", "date_added")
    date_hierarchy = "date_added"


@admin.register(LadderSubscription)
class LadderSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("ladder", "user", "subscribed_at")
    search_fields = ("ladder__season__name", "user__email")
    ordering = ("ladder",)

@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "email", "status", "ability_note", "created_at")
    search_fields = ("first_name", "last_name", "email", "ability_note")
    list_filter = ("status",)
    ordering = ("last_name", "first_name")