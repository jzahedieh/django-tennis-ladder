import django_tables2 as tables
import itertools
from .models import League

class LeagueResultTable(tables.Table):
    row_number = tables.Column(empty_values=())
    id = tables.Column

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.counter = itertools.count()

    def render_row_number(self):
        return next(self.counter) + 1

    def render_id(self, value):
        return "<%s>" % value