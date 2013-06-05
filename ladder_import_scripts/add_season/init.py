from ladder.models import Season, Player, Ladder, Result
import datetime

season = Season.objects.get(pk=3)

with open('/home/jon/workspace/python_projects/tennis/ladder_import_scripts/add_season/data/prepared') as f:
	names = f.readlines()

for name in names:
	split = name.split()
	first_name = ''
	last_name = ''
	if split[0] == "DIVISION":
		current_ladder = split[1]
		print current_ladder
		ladder = Ladder(season=season, division=current_ladder, ladder_type="First to 9")
		ladder.save()
	else:
		if len(split) == 2 and split[0] != "DIVISION":
			print split[1]

		elif len(split) == 3:
			first_name = split[1]
			last_name = split[2]
		elif len(split) == 4:
			first_name = split[1]
			last_name = split[2]


		#player.save()
		#ladder.players.add(player)

		try:
			player_object = Player.objects.get(first_name=first_name, last_name=last_name)
		except:
			print 'No match for player: ' + first_name + last_name
			try:
				player_object = Player(first_name=first_name, last_name=last_name)
				player_object.save()
			except:
				print 'Failed to create player: ' + first_name + last_name

		ladder.players.add(player_object)

	first_name = ''
	last_name = ''