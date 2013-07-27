from xlrd import open_workbook
from ladder.models import Season, Player, Ladder, Result, League
from collections import defaultdict
import datetime

book = open_workbook(
    '/home/jon/workspace/python_projects/tennis/ladder_import_scripts/xls/files/ladderSep-Dec2009Results.xls')

season = Season.objects.get(pk=14)  # hard code season as have to create manually
sh1 = book.sheet_by_index(0)  # sheet1, aways first sheet
player_list = defaultdict(dict)  # initialize defaultdict for our player list.
current_div = 0  # set the division counter to 0

# save all players then set up ladder
for rownum in range(sh1.nrows):
    rows = sh1.row_values(rownum)

    #Find out division numbers
    if not rows[0] and rows[1] != 'NAME' and rows[1] != 'ROUND':
        for div in rows:
            if isinstance(div, float):
                current_div = div
                try:
                    ladder = Ladder.objects.get(season=season, division=div)
                except:
                    ladder = Ladder(season=season, division=div, ladder_type="First to 9")
                    ladder.save()


    #save players
    if rows[0] and rows[1] != 'NAME':
        position = rows[0]
        first_name = rows[1]
        last_name = rows[2]
        #print first_name, last_name, position

        #populate our array for later use
        player_list[current_div][position] = {'first_name': first_name, 'last_name': last_name}

        try:
            player_object = Player.objects.get(first_name=first_name, last_name=last_name)
        except:
            print 'No match for player: ' + first_name + last_name
            try:
                player_object = Player(first_name=first_name, last_name=last_name)
                player_object.save()
            except:
                print 'Failed to create player: ' + first_name + last_name


        try:
            league_object = League.objects.get(ladder=ladder, player=player_object)
        except League.MultipleObjectsReturned:
            pass
        except:
            league_object = League.objects.create(ladder=ladder, player=player_object, sort_order=position * 10)

print 'built good'

current_div = 0  # reset the division counter to 0
# save the results
for rownum in range(sh1.nrows):

    rows = sh1.row_values(rownum)

    #Well lazy copy pasta for division info
    if not rows[0] and rows[1] != 'NAME' and rows[1] != 'ROUND':
        for div in rows:
            if isinstance(div, float):
                current_div = div

    if rows[1] == 'NAME':
        i = 3
        while rows[i] != 'Div':
            i += 1

        count = i - 3

    if rows[0]:
        position = rows[0]
        first_name = rows[1]
        last_name = rows[2]

        #print id, name1, name2
        for c in range(count):

            if rows[c + 3]:
                score = rows[c + 3]

                if not isinstance(score, float):
                    break

                opp_last_name = player_list[current_div][c + 1]['last_name']
                opp_first_name = player_list[current_div][c + 1]['first_name']


                #print str(id) + ' vs ' + str(c) + ' score: ' + str(rows[c+3])
                try:
                    ladder_object = Ladder.objects.get(season=season, division=int(current_div))
                except:
                    print 'No ladder matching: ' + ' ' + str(current_div)
                    break
                try:
                    player_object = Player.objects.get(first_name=first_name, last_name=last_name)
                except:
                    print 'No match for player: ' + first_name + last_name
                try:
                    opp_object = Player.objects.get(first_name=opp_first_name, last_name=opp_last_name)
                except:
                    print 'No match for opp: ' + opp_first_name + opp_last_name
                    #print str(season_pk) + ' ' +division_no + ': ' + first_name + last_name + ' vs ' +opp_first_name + opp_last_name + ' ' +  str(r)

                try:
                    result_object = Result.objects.get(ladder=ladder_object, player=player_object, opponent=opp_object)
                except Result.MultipleObjectsReturned:
                    pass
                except:
                    result_object = Result(ladder=ladder_object, player=player_object, opponent=opp_object,
                                           result=score, date_added=datetime.datetime.now())
                    result_object.save()
