import django_tables2 as tables
import itertools
from .models import League

class LeagueResultTable(tables.Table):
    row_number = tables.Column(empty_values=())
    name = tables.Column()

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.counter = itertools.count()

    def render_row_number(self):
        return next(self.counter) + 1

    def render_id(self, value):
        return "<%s>" % value

class TestTable(tables.Table):
    id = tables.Column()
    name = tables.Column()
    player_1 = tables.Column()
    player_2 = tables.Column()
    player_3 = tables.Column()
    player_4 = tables.Column()
    player_5 = tables.Column()
    player_6 = tables.Column()
    player_7 = tables.Column()
    player_8 = tables.Column()
    player_9 = tables.Column()
    player_10 = tables.Column()
    player_11 = tables.Column()
