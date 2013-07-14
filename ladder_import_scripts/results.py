from ladder.models import Season, Player, Ladder, Result

import datetime
from collections import defaultdict
from collections import Counter

season_pk = 2
score_pos = {}
division_list = {}
division_next = False
ten_gone = False
el_gone = False
player_list = defaultdict(dict)

with open('/home/jon/Downloads/ladder/python/prev') as f:
    ladder = f.readlines()

for person in ladder:
    names = person.split()

    if 'DIVISION' in person:
        ladder_div = names[1]
    elif names[2] != '3':
        pass
        player_list[ladder_div][names[0]] = {'fname': names[1], 'sname': names[2]}

for player in ladder:
    line = list(player)
    words = player.split()
    #find out which characters hold information
    if division_next == True:
        division_list = list(player)
        division_next = False

    for counter, char in enumerate(division_list):
        #if 1
        if char == '1' and counter <= 70:
            score_pos[1] = counter
        #if 11
        if char == '1' and ten_gone == True and el_gone == False:
            el_gone = True
            score_pos[11] = counter
        #if 10
        if char == '1' and counter >= 70 and ten_gone == False:
            ten_gone = True
            score_pos[10] = counter
        #for 2-9
        for i in range(2, 9):
            if char == str(i):
                score_pos[i] = counter
    ten_gone = False
    el_gone = False

    results = {}
    for key, val in score_pos.iteritems():
        try:
            if line[val] == ' ':
                results[key] = '-'
            else:
                results[key] = line[val]
        except:
            #freaks out at 'DIVISION'
            pass
    #print results

    if 'DIVISION' in player:
        division_no = words[1]
        division_next = True
    elif words[2] != '3':
        first_name = words[1]
        last_name = words[2]
        season_object = Season.objects.get(pk=season_pk)

        position = words[0]
        for k, r in results.iteritems():
            opp_last_name = player_list[division_no][str(k)]['sname']
            opp_first_name = player_list[division_no][str(k)]['fname']
            if r != '-':
                try:
                    ladder_object = Ladder.objects.get(season=season_object, division=int(division_no))
                except:
                    print 'No ladder matching: ' + season_pk + ' ' + division_no
                try:
                    player_object = Player.objects.get(first_name=first_name, last_name=last_name)
                except:
                    print 'No match for player: ' + first_name + last_name
                try:
                    opp_object = Player.objects.get(first_name=opp_first_name, last_name=opp_last_name)
                except:
                    print 'No match for opp: ' + opp_first_name + opp_last_name
                #print str(season_pk) + ' ' +division_no + ': ' + first_name + last_name + ' vs ' +opp_first_name + opp_last_name + ' ' +  str(r)

                result_object = Result(ladder=ladder_object, player=player_object, opponent=opp_object, result=int(r),
                                       date_added=datetime.date(2013, 03, 29))
                result_object.save()

    results.clear()
    score_pos.clear()
