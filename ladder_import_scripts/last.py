from ladder.models import Season, Player, Ladder, Result
import datetime

with open('/home/jon/Downloads/ladder/python/prev') as f:
	ladder = f.readlines()

score_pos = {}
division_list = {}
division_next = False
ten_gone = False
el_gone = False

season = Season.objects.get(pk=2)

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

from collections import defaultdict


class Tree(defaultdict):
	def __init__(self, value=None):
		super(Tree, self).__init__(Tree)
		self.value = value


root = Tree()
root.value = 1
root['a']['b'].value = 3
print root.value
print root['a']['b'].value
print root['c']['d']['f'].value
