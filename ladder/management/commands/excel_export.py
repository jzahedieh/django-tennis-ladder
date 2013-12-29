from xlwt import *
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import os


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


class Command(BaseCommand):
    help = 'Exports XLS, args: year and round'
    option_list = BaseCommand.option_list + (
        make_option('--year',
                    action='store',
                    dest='year',
                    default=False,
                    help='Year of ladder'),
    ) + (
        make_option('--round',
                    action='store',
                    dest='round',
                    default=False,
                    help='Round of ladder'),
    )

    def handle(self, *args, **options):

        def getkey(value, arg):
            try:
                return value[arg]
            except KeyError:
                return {}

        # where generated files will be saved
        folder = 'E:\\projects\\django-tennis-ladder\\ladder_import_scripts\\xls\\files'

        if os.access(folder, os.W_OK) is False:
            raise CommandError('Directory (%s) is not writeable, change in code' % folder)

        # make arg checks
        if options['year'] is False:
            raise CommandError('--year option not set')

        if options['round'] is False:
            raise CommandError('--round option not set')

        # workbook setup stuff
        w = Workbook(encoding='utf-8')
        ws = w.add_sheet('Sheet 1')

        font0 = Font()
        font0.name = 'Times New Roman'
        font0.height = 280
        font0.bold = True

        font1 = Font()
        font1.name = 'Times New Roman'
        font1.height = 400
        font1.bold = True

        style0 = XFStyle()
        style0.font = font0
        style1 = XFStyle()
        style1.font = font1

        #Grey box
        pattern = Pattern()
        pattern.pattern = Pattern.SOLID_PATTERN
        pattern.pattern_fore_colour = Style.colour_map['gray40']

        grey_box_style = XFStyle()
        grey_box_style.pattern = pattern

        # export
        export = Export(options['year'], options['round'])
        col = 1

        ws.row(1).height_mismatch = 1
        ws.row(1).height = 600
        ws.col(0).width = 256 * 5

        ws.write(col, 1, 'ROUND', style1)
        ws.write(col, 2, str(export.season.season_round), style1)
        ws.write(col, 5, export.season.start_date.strftime('%b') + ' - ' + export.season.end_date.strftime('%d %B %Y'), style1)

        for ladder in export.ladders:
            col += 2
            ws.row(col).height_mismatch = 1
            ws.row(col).height = 450
            ws.write(col, 5, 'DIVISION', style0)
            ws.write(col, 8, ladder.division.__str__(), style0)
            ws.write(col, 14, 'LAST ROUND', style0)

            col += 1
            ws.row(col).height_mismatch = 1
            ws.row(col).height = 450
            ws.write(col, 1, 'NAME', style0)
            ws.col(1).width = 256 * 16
            ws.col(2).width = 256 * 26

            #col width for results
            for i in range(3, 25):
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

            ws.write(col, 2 + count, 'Div', style0)
            ws.write(col, 2 + count + 1, 'PLD', style0)
            ws.write(col, 2 + count + 2, 'WON', style0)
            ws.write(col, 2 + count + 3, 'TOTAL', style0)

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
                        ws.write(col, row, '', grey_box_style)
                    else:
                        # result
                        for result in getkey(export.results, league.player.id):
                            if league.player.id == result.player.id and opponent.player.id == result.opponent.id:
                                ws.write(col, row, result.result, style0)

                    row += 1
                    column_counter += 1

                # populate formula's
                frow = (col + 1).__str__()

                #pld / won
                last_l = chr(row + ord("A") - 1)
                ws.write(col, row, league.ladder.division, style0)
                ws.write(col, row + 1, Formula('COUNT(D' + frow + ':' + last_l + frow + ')'), style0)
                ws.write(col, row + 2, Formula('COUNTIF(D' + frow + ':' + last_l + frow + ',9)'), style0)

                # total
                pld_l = chr(row + 2 + ord("A") - 1)
                won_l = chr(row + 3 + ord("A") - 1)
                ws.write(col, row + 3,
                         Formula('SUM(D' + frow + ':' + last_l + frow + ') + ' + pld_l + frow + ' + (' + won_l + frow + '*2)'),
                         style0)

                player_counter += 1

            #won stats
            last_r = chr(total_won_row - 4 + ord("A") - 1)
            ws.write(total_won_col, total_won_row,
                     Formula('COUNTIF(D' + total_played_col.__str__() + ':' + last_r + (col + 1).__str__() + ',9)'), style0)
            ws.write(total_played_col, total_played_row,
                     Formula('COUNT(D' + total_played_col.__str__() + ':' + last_r + (col + 1).__str__() + ')'), style0)

        filename = 'ladder' + export.season.start_date.strftime('%b') + '-' + export.season.end_date.strftime('%b%Y') + 'Results.xls'
        w.save(folder + filename)