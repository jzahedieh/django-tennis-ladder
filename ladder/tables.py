import django_tables2 as tables

class LeagueResultTable(tables.Table):
    id = tables.Column()
    name = tables.Column()
