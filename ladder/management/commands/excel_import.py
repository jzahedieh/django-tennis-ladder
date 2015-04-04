from collections import defaultdict
from optparse import make_option
import os

from xlrd import open_workbook
from django.core.management.base import BaseCommand, CommandError

from ladder.models import Season, Player, Ladder, Result, League


class Command(BaseCommand):
    help = u'Exports XLS, args: --season'
    option_list = BaseCommand.option_list + (
        make_option(u'--season',
                    action=u'store',
                    dest=u'season',
                    default=False,
                    help=u'ID of season'),
    )

    def handle(self, *args, **options):

        file_location = u"/home/input/projects/django-tennis-ladder/ladder_import_scripts/xls/files/import.xls"

        if os.access(file_location, os.R_OK) is False:
            raise CommandError(u'Directory (%s) is not writeable, change in code' % file_location)

        # make arg checks
        if options[u'season'] is False:
            raise CommandError(u'--season id option not set')

        book = open_workbook(file_location)

        season = Season.objects.get(pk=options[u'season'])
        sh1 = book.sheet_by_index(0)  # sheet1, aways first sheet
        player_list = defaultdict(dict)  # initialize defaultdict for our player list.
        current_div = {}  # set the division counter to 0

        # save all players then set up ladder
        for rownum in xrange(sh1.nrows):
            rows = sh1.row_values(rownum)

            #Find out division numbers
            if not rows[0] and rows[1] != u'NAME' and rows[1] != u'ROUND':
                for div in rows:
                    if isinstance(div, float):
                        current_div = (u'%.2f' % div).rstrip(u'0').rstrip(u'.')
                        try:
                            ladder = Ladder.objects.get(season=season, division=current_div)
                        except:
                            ladder = Ladder(season=season, division=current_div, ladder_type=u"First to 9")
                            ladder.save()

            #save players
            if rows[0] and rows[1] != u'NAME':
                position = rows[0]
                first_name = rows[1]
                last_name = rows[2]

                #populate our array for later use
                player_list[current_div][position] = {u'first_name': first_name, u'last_name': last_name}

                try:
                    player_object = Player.objects.get(first_name=first_name, last_name=last_name)
                except:
                    print u'No match for player: ' + first_name + last_name
                    try:
                        player_object = Player(first_name=first_name, last_name=last_name)
                        player_object.save()
                    except:
                        print u'Failed to create player: ' + first_name + last_name

                try:
                    league_object = League.objects.get(ladder=ladder, player=player_object)
                except League.MultipleObjectsReturned:
                    pass
                except:
                    league_object = League.objects.create(ladder=ladder, player=player_object, sort_order=position * 10)

        print u'built good'

        current_div = {}  # reset the division counter to 0
        # save the results
        for rownum in xrange(sh1.nrows):

            try:
                rows = sh1.row_values(rownum)

                #Well lazy copy pasta for division info
                if not rows[0] and rows[1] != u'NAME' and rows[1] != u'ROUND':
                    for div in rows:
                        if isinstance(div, float):
                            current_div = (u'%.2f' % div).rstrip(u'0').rstrip(u'.')
                            print current_div

                if rows[1] == u'NAME':
                    i = 3
                    while rows[i] != u'Div':  # flag to end scores normally 'Div'
                        i += 1

                    count = i - 3

                if rows[0]:
                    try:
                        position = rows[0]
                        first_name = rows[1]
                        last_name = rows[2]
                    except:
                        print u'index error for row: ' + rows[0]

                    for c in xrange(count):

                        if rows[c + 3] != u'':
                            score = rows[c + 3]

                            if not isinstance(score, float):
                                continue

                            opp_last_name = player_list[current_div][c + 1][u'last_name']
                            opp_first_name = player_list[current_div][c + 1][u'first_name']

                            try:
                                ladder_object = Ladder.objects.get(season=season, division=current_div)
                            except:
                                print u'No ladder matching: ' + u' ' + unicode(current_div)
                                break
                            try:
                                player_object = Player.objects.get(first_name=first_name, last_name=last_name)
                            except:
                                print u'No match for player: ' + first_name + last_name
                            try:
                                opp_object = Player.objects.get(first_name=opp_first_name, last_name=opp_last_name)
                            except:
                                print u'No match for opp: ' + opp_first_name + opp_last_name

                            try:
                                result_object = Result.objects.get(ladder=ladder_object, player=player_object,
                                                                   opponent=opp_object)
                            except Result.MultipleObjectsReturned:
                                pass
                            except:
                                result_object = Result(ladder=ladder_object, player=player_object, opponent=opp_object,
                                                       result=score, date_added=season.end_date)
                                result_object.save()
            except Exception, e:
                print u'problem @ row: ' + rownum.__str__() + e.__str__()
                raise CommandError(e.__str__())
