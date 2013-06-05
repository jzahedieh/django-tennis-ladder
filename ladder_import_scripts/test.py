from collections import defaultdict
from collections import Counter

season_pk = 2
score_pos = {}
division_list = {}
division_next = False
ten_gone = False
el_gone = False
d = defaultdict(dict)


def multi_dimensions(n, type):
	""" Creates an n-dimension dictionary where the n-th dimension is of type 'type'
	  """
	if n <= 1:
		return type()
	return defaultdict(lambda: multi_dimensions(n - 1, type))


player_list = multi_dimensions(2, Counter)

with open('/home/jon/Downloads/ladder/python/prev') as f:
	ladder = f.readlines()

for person in ladder:
	names = person.split()

	if 'DIVISION' in person:
		ladder_div = names[1]
	elif names[2] != '3':
		d[ladder_div][names[0]] = {'fname': names[1], 'sname': names[2]}
		player_list[ladder_div][names[0]] = {'fname': names[1], 'sname': names[2]}

print player_list['1']['1']
print d['1']['1']
