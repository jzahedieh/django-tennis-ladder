from xlwt import *
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import os


class Export(object):
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


class Command(BaseCommand):
    help = u'Exports XLS, args: year and round'
    option_list = BaseCommand.option_list + (
        make_option(u'--year',
                    action=u'store',
                    dest=u'year',
                    default=False,
                    help=u'Year of ladder'),
    ) + (
        make_option(u'--round',
                    action=u'store',
                    dest=u'round',
                    default=False,
                    help=u'Round of ladder'),
    )

    def handle(self, *args, **options):

        def getkey(value, arg):
            try:
                return value[arg]
            except KeyError:
                return {}

        # where generated files will be saved
        folder = u'/home/input/projects/django-tennis-ladder/ladder_import_scripts/xls/files'

        if os.access(folder, os.W_OK) is False:
            raise CommandError(u'Directory (%s) is not writeable, change in code' % folder)

        # make arg checks
        if options[u'year'] is False:
            raise CommandError(u'--year option not set')

        if options[u'round'] is False:
            raise CommandError(u'--round option not set')

        # workbook setup stuff
        w = Workbook(encoding=u'utf-8')
        ws = w.add_sheet(u'Sheet 1')

        font0 = Font()
        font0.name = u'Times New Roman'
        font0.height = 280
        font0.bold = True

        font1 = Font()
        font1.name = u'Times New Roman'
        font1.height = 400
        font1.bold = True

        style0 = XFStyle()
        style0.font = font0
        style1 = XFStyle()
        style1.font = font1

        #Grey box
        pattern = Pattern()
        pattern.pattern = Pattern.SOLID_PATTERN
        pattern.pattern_fore_colour = Style.colour_map[u'gray40']

        grey_box_style = XFStyle()
        grey_box_style.pattern = pattern

        #Red box
        pattern = Pattern()
        pattern.pattern = Pattern.SOLID_PATTERN
        pattern.pattern_fore_colour = Style.colour_map[u'red']

        inaccurate_style = XFStyle()
        inaccurate_style.pattern = pattern
        inaccurate_style.font = font0

        # export
        export = Export(options[u'year'], options[u'round'])
        col = 1

        ws.row(1).height_mismatch = 1
        ws.row(1).height = 600
        ws.col(0).width = 256 * 5

        ws.write(col, 1, u'ROUND', style1)
        ws.write(col, 2, unicode(export.season.season_round), style1)
        ws.write(col, 5, export.season.start_date.strftime(u'%b') + u' - ' + export.season.end_date.strftime(u'%d %B %Y'), style1)

        for ladder in export.ladders:
            col += 2
            ws.row(col).height_mismatch = 1
            ws.row(col).height = 450
            ws.write(col, 5, u'DIVISION', style0)
            ws.write(col, 8, ladder.division.__str__(), style0)
            ws.write(col, 14, u'LAST ROUND', style0)

            col += 1
            ws.row(col).height_mismatch = 1
            ws.row(col).height = 450
            ws.write(col, 1, u'NAME', style0)
            ws.col(1).width = 256 * 16
            ws.col(2).width = 256 * 26

            #col width for results
            for i in xrange(3, 25):
                ws.col(i).width = 256 * 6

            # names and row numbers
            count = 1
            for i in ladder.league_set.all():
                ws.col(col + count).width = 256 * 26
                ws.row(col + count).height_mismatch = 1
                ws.row(col + count).height = 450
                # row numbers and name
                ws.write(col + count, 0, count, style0)
                ws.write(col + count, 1, i.player.first_name, style0)
                ws.write(col + count, 2, i.player.last_name, style0)
                # col numbers
                ws.write(col, 2 + count, count, style0)
                count += 1

            ws.write(col, 2 + count, u'Div', style0)
            ws.write(col, 2 + count + 1, u'PLD', style0)
            ws.write(col, 2 + count + 2, u'WON', style0)
            ws.write(col, 2 + count + 3, u'TOTAL', style0)

            # total won col/row for later use
            total_won_col = col + 1
            total_won_row = 2 + count + 4
            # total played col/row for later use
            total_played_col = col + 2
            total_played_row = 2 + count + 4

            player_counter = 0
            for league in ladder.league_set.all():
                col += 1
                row = 3
                # loop through players
                column_counter = 0  # disable for now, think can use other count for greybox check
                for opponent in ladder.league_set.all():
                    # loop through op
                    if column_counter == player_counter:
                        ws.write(col, row, u'', grey_box_style)
                    else:
                        # result
                        for result in getkey(export.results, league.player.id):
                            if league.player.id == result.player.id and opponent.player.id == result.opponent.id:
                                if result.inaccurate_flag:
                                    ws.write(col, row, result.result, inaccurate_style)
                                else:
                                    ws.write(col, row, result.result, style0)

                    row += 1
                    column_counter += 1

                # populate formula's
                frow = (col + 1).__str__()

                #pld / won
                last_l = unichr(row + ord(u"A") - 1)
                ws.write(col, row, league.ladder.division, style0)
                ws.write(col, row + 1, Formula(u'COUNT(D' + frow + u':' + last_l + frow + u')'), style0)
                ws.write(col, row + 2, Formula(u'COUNTIF(D' + frow + u':' + last_l + frow + u',9)'), style0)

                # total
                pld_l = unichr(row + 2 + ord(u"A") - 1)
                won_l = unichr(row + 3 + ord(u"A") - 1)
                ws.write(col, row + 3,
                         Formula(u'SUM(D' + frow + u':' + last_l + frow + u') + ' + pld_l + frow + u' + (' + won_l + frow + u'*2)'),
                         style0)

                player_counter += 1

            #won stats
            last_r = unichr(total_won_row - 4 + ord(u"A") - 1)
            ws.write(total_won_col, total_won_row,
                     Formula(u'COUNTIF(D' + total_played_col.__str__() + u':' + last_r + (col + 1).__str__() + u',9)'), style0)
            ws.write(total_played_col, total_played_row,
                     Formula(u'COUNT(D' + total_played_col.__str__() + u':' + last_r + (col + 1).__str__() + u')'), style0)

        filename = u'ladder' + export.season.start_date.strftime(u'%b') + u'-' + export.season.end_date.strftime(u'%b%Y') + u'Results.xls'
        w.save(folder + filename)