from django.contrib import admin
from ladder.models import Season, Player, Ladder, Result


class SeasonAdmin(admin.ModelAdmin):
    pass


admin.site.register(Season)


class PlayerAdmin(admin.ModelAdmin):
    pass


admin.site.register(Player)


class LadderAdmin(admin.ModelAdmin):
    pass


admin.site.register(Ladder)


class ResultAdmin(admin.ModelAdmin):
    pass


admin.site.register(Result)
