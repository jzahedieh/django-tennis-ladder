__author__ = 'jay-zee'
from xlwt import *

class Export:
    def __init__(self, year, season_round):
        from ladder.models import Ladder, Result, Season, League

        season = Season.objects.get(start_date__year=year, season_round=season_round)

        ladders = Ladder.objects.filter(season=season)

        results = Result.objects.filter(ladder__season=season)
        league = League.objects.filter(ladder__season=season)

        results_dict = {}

        for result in results:
            results_dict.setdefault(result.player.id, []).append(result)

        self.season = season
        self.ladders = ladders
        self.results = results_dict
        self.league = league

def getkey(value, arg):
    try:
        return value[arg]
    except:
        return {}

# workbook setup stuff
w = Workbook()
ws = w.add_sheet('Sheet 1')

font0 = Font()
font0.name = 'Times New Roman'
font0.height = 200 #280 14px
font0.bold = True

style0 = XFStyle()
style0.font = font0

# export
export = Export(2013, 2)
col = 1

ws.write(col, 1, 'ROUND', style0)
ws.write(col, 2, str(export.season.season_round), style0)
ws.write(col, 65, export.season.start_date.__str__() + ' - ' + export.season.end_date.__str__()), style0

for ladder in export.ladders:
    col += 2
    ws.write(col, 5, 'DIVISION', style0)
    ws.write(col, 8, ladder.division.__str__(), style0)

    col += 1
    ws.write(col, 1, 'NAME', style0)

    # names and row numbers
    count = 1
    for i in ladder.league_set.all():
        # row numbers and name
        ws.write(col + count, 0, count, style0)
        ws.write(col + count, 1, i.player.first_name, style0)
        ws.write(col + count, 2, i.player.last_name, style0)
        # col numbers
        ws.write(col, 2 + count, count, style0)
        count += 1

    ws.write(col, 2 + count, 'TOTAL', style0)

    player_counter = 0
    for league in ladder.league_set.all():
        col += 1
        row = 3
        # loop through players
        column_counter = 100 #disable for now, think can use other count for greybox check
        for opponent in ladder.league_set.all():
            # loop through op
            if column_counter == player_counter:
                pass # grey box
            else:
                # result
                for result in getkey(export.results, league.player.id):
                    if league.player.id == result.player.id and opponent.player.id == result.opponent.id:
                        ws.write(col, row, result.result, style0)
            row += 1

w.save('/var/www/tennis/ladder_import_scripts/xls/tmp.xls')