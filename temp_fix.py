import fileinput
import sys

for line in fileinput.input('ains/db.py', inplace=True):
    if '"sqlite:///./test_ains_temp.db"' in line:
        print(line.replace('test_ains_temp.db', 'ains.db'), end='')
    else:
        print(line, end='')
