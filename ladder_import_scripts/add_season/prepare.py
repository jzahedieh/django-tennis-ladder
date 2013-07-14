__author__ = 'jon'

# To get a file in the state of output use pdftotext -layout [pdf] output
# Not perfect prepared will need a manual check after.
#

import os

with open('/home/jon/workspace/python_projects/tennis/ladder_import_scripts/add_season/data/output') as f:
    names = f.readlines()

w = open('/home/jon/workspace/python_projects/tennis/ladder_import_scripts/add_season/data/prepared', 'w')

for name in names:
    split = name.split()
    flag = 0
    i = 0
    ret = ''

    for part in split:
        i = i + 1
        if part.isalnum():
            flag = flag + 1

        if flag == 3:
            break

    for count in range(i):
        if split[count] != 'LAST':
            ret = ret + ' ' + split[count]

    if ret != ' NAME 1 2':
        if ret != '':
            w.write(ret + os.linesep)

    flag = 0
    i = 0
    ret = ''

w.close()