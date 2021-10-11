#!/usr/bin/python3

import sys
import os
import subprocess
import re
from datetime import date
import datetime
import zipfile
from dbconnect import getConnection

dates = re.compile('2021[0-9]*') # 2021 records
cmd='aws --profile resnet s3 ls s3://psweb-data-updates/mammal/resnet16/'
downloadcmd='aws --profile resnet s3 cp s3://psweb-data-updates/mammal/resnet16/xxxx  .'

pdir = os.path.dirname(os.path.realpath(__file__)) # dir of this program

def runcmd(cmd):
    result = []
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        result.append(line.decode('utf8').strip())
    retval = p.wait()
    return result;


def printlist(mlist):
    for i in mlist:
        print(i)


# mammal-update-20211002-Viruses.rnef.zip
filelist = runcmd(cmd)
latest_date = date(1900,1,1)
database = {}

for item in filelist:
    if not item.endswith('zip'):
        continue

    elems = item.split()
    if len(elems) >= 4 :
        fname = elems[3]
        if not '2021' in fname:
            continue

        tdate = dates.findall(fname)[0]
        year = int(tdate[:4])
        month = int(tdate[4:6])
        day = int(tdate[6:8])
        d = date(year, month, day)

        if not str(d) in database:
            database[str(d)] = []

        database[str(d)].append(fname);
        if d > latest_date:
            latest_date = d

#-------------------------------------------------------
print('latest update', latest_date)
        
latest = database[str(latest_date)]

for i in latest:
    print('downloading',i)
    cmd = re.sub('xxxx',i,downloadcmd)
    msg = runcmd(cmd)
    printlist(msg)

    with zipfile.ZipFile(i, 'r') as zipp:
        zipp.extractall('.')

    os.remove(i)
    msg = runcmd(pdir + '/readresnet.py ' + i[:-4] + ' False')
    printlist(msg)

print('---')
msg = runcmd(pdir + '/create_tables.py  resnet_temp')
printlist(msg)



