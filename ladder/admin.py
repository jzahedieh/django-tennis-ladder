from django.contrib import admin
from ladder.models import Season, Player, Ladder, Result, League
from django.db import transaction
from django.db.models import get_models, Model
from django.contrib.contenttypes.generic import GenericForeignKey


class SeasonAdmin(admin.ModelAdmin):
    list_display = (u'name', u'start_date', u'end_date', u'season_round')
    date_hierarchy = u'start_date'


admin.site.register(Season, SeasonAdmin)

class PlayerAdmin(admin.ModelAdmin):
    list_display = (u'first_name', u'last_name')
    search_fields = (u'first_name', u'last_name')
    ordering = ('last_name',)


admin.site.register(Player, PlayerAdmin)


class LadderAdmin(admin.ModelAdmin):
    list_filter = [u'season']
    list_display = (u'season', u'division')


admin.site.register(Ladder, LadderAdmin)


class LeagueAdmin(admin.ModelAdmin):
    list_filter = [u'ladder__season']
    list_display = (u'get_player', u'get_season', u'get_division', u'sort_order')
    search_fields = (u'player__first_name', u'player__last_name')
    ordering = ('ladder__season__start_date', 'ladder__division', 'sort_order')

    def get_season(self, league):
        return league.ladder.season

    def get_division(self, league):
        return league.ladder.division

    def get_player(self, league):
        return league.player.first_name + ' ' + league.player.last_name

    get_season.short_description = "Season"
    get_season.admin_order_field = "ladder__season__start_date"
    get_division.short_description = "Division"
    get_division.admin_order_field = "ladder__division"
    get_player.short_description = "Player"
    get_player.admin_order_field = "player"

admin.site.register(League, LeagueAdmin)


class ResultAdmin(admin.ModelAdmin):
    list_filter = [u'ladder__season']
    search_fields = [u'player__first_name', u'player__last_name']
    list_display = (u'ladder', u'player', u'opponent', u'result', u'date_added')
    date_hierarchy = u'date_added'


admin.site.register(Result, ResultAdmin)