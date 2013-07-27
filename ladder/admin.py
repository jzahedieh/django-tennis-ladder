from django.contrib import admin
from ladder.models import Season, Player, Ladder, Result, League


class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')
    date_hierarchy = 'start_date'


admin.site.register(Season, SeasonAdmin)


class PlayerAdmin(admin.ModelAdmin):
    search_fields = ('first_name', 'last_name')


admin.site.register(Player, PlayerAdmin)


class LadderAdmin(admin.ModelAdmin):
    list_filter = ['season']
    list_display = ('season', 'division')


admin.site.register(Ladder, LadderAdmin)

class LeagueAdmin(admin.ModelAdmin):
    list_filter = ['ladder']
    list_display = ('player', 'ladder', 'sort_order')
    search_fields = ('player', 'ladder')


admin.site.register(League, LeagueAdmin)


class ResultAdmin(admin.ModelAdmin):
    search_fields = ['player__first_name', 'player__last_name']
    list_display = ('ladder', 'player', 'opponent', 'result', 'date_added')
    date_hierarchy = 'date_added'


admin.site.register(Result, ResultAdmin)
