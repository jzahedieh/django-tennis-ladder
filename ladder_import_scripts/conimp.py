from ladder.models import Season, Player, Ladder, Position, Result

with open('/home/jon/workspace/python_projects/tennis/ladder_import_scripts/contact') as f:
	contacts = f.readlines()

for contact in contacts:
	split = contact.split()
	person = {}
	for (counter, c) in enumerate(split):
		if c == split[0]:
			person['first_name'] = c
		elif c == split[1]:
			person['last_name'] = c
		elif c[:2] == '07':
			person['mobile_no'] = c
		elif '@' in c:
			person['email'] = c
		else:
			person['home_no'] = c

	try:
		player = Player.objects.get(first_name=person['first_name'], last_name=person['last_name'].upper())
		for key, val in person.iteritems():
			if key == 'home_no':
				player.home_phone = val
			if key == 'mobile_no':
				player.mobile_phone = val
			if key == 'email':
				player.email = val
			player.save()
	except:
		print person['first_name'] + ' ' + person['last_name'].upper() + ' no match!'
