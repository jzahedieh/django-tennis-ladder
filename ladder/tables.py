import django_tables2 as tables


class LeagueResultTable(tables.Table):
    class Meta:
        attrs = {"class": "ladderTable"}
        default = ''

    id = tables.Column(verbose_name='', attrs={"td": {"class": "player_position"}})
    name = tables.Column(attrs={"td": {"class": "player_name"}})
