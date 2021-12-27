from django.contrib import admin
from ladder.models import Season, Player, Ladder, Result, League, LadderSubscription


class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'season_round')
    date_hierarchy = 'start_date'


admin.site.register(Season, SeasonAdmin)


class PlayerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name')
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name',)


admin.site.register(Player, PlayerAdmin)


class LadderAdmin(admin.ModelAdmin):
    list_filter = ['season']
    list_display = ('season', 'division')
    ordering = ("season", "division")


admin.site.register(Ladder, LadderAdmin)


class LeagueAdmin(admin.ModelAdmin):
    list_filter = ['ladder__season']
    list_display = ('get_player', 'get_season', 'get_division', 'sort_order')
    search_fields = ('player__first_name', 'player__last_name')
    ordering = ('-ladder__season__start_date', 'ladder__division', 'sort_order')

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
    list_filter = ['ladder__season']
    search_fields = ['player__first_name', 'player__last_name']
    list_display = ('ladder', 'get_player', 'get_opponent', 'result', 'date_added')
    date_hierarchy = 'date_added'

    def get_player(self, result):
        return result.player.first_name + ' ' + result.player.last_name

    def get_opponent(self, result):
        return result.opponent.first_name + ' ' + result.opponent.last_name

    get_player.short_description = "Player"
    get_player.admin_order_field = "player"
    get_player.short_description = "Opponent"
    get_player.admin_order_field = "opponent"


admin.site.register(Result, ResultAdmin)


class LadderSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('ladder', 'user', 'subscribed_at')
    search_fields = ('ladder', 'user')
    ordering = ('ladder',)


admin.site.register(LadderSubscription, LadderSubscriptionAdmin)