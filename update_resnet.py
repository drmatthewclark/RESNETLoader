#!/usr/bin/python3

import sys
import os
import subprocess
import re
from datetime import date
import datetime
import zipfile
from dbconnect import getConnection
from dbconnect import psql_cmd

dates = re.compile('2022[0-9]*') # 2021 records
cmd='aws --profile resnet s3 ls s3://psweb-data-updates/mammal/resnet17/'
downloadcmd='aws --profile resnet s3 cp s3://psweb-data-updates/mammal/resnet17/xxxx  .  --no-progress'

pdir = os.path.dirname(os.path.realpath(__file__)) # dir of this program
files_downloaded = 0

def runcmd(cmd):
    result = []
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        result.append(line.decode('utf8').strip())
    retval = p.wait()
    return result;


def printlist(mlist):
    for i in mlist:
        #print(i)
        pass

def checkthisupdate(this_date):
    """ check to see if this update has alrady been added"""
    thisrec = ('update', str(this_date))
    conn = getConnection()
    with conn.cursor() as cur:
        cur.execute('select name, value from resnet.version where name = %s and value::date >= %s::date', thisrec)
        if cur.rowcount > 0:
            return True 
       
    conn.close()
    return False


# mammal-update-20211002-Viruses.rnef.zip

def getfiles():

    database = {}
    filelist = runcmd(cmd)
    for item in filelist:
    
        if not item.endswith('zip'):
            continue
    
        elems = item.split()
    
        if len(elems) >= 4 :
            fname = elems[3]
            if not '2022' in fname:
                continue
    
            tdate = elems[0]
            #  2022-01-01
            year = int(tdate[0:4])
            month = int(tdate[5:7])
            day  = int(tdate[8:10])
            print(tdate, 'year', year, 'month', month, 'day', day)
            d = date(year, month, day)
            database[fname] = d

    # return map of filename and their file dates   
    return database 
#-------------------------------------------------------


def process_files():
    
    global files_downloaded

    database = getfiles()
    # set of unique dates from files
    dates  = set(database.values())

    for file in database:
    
        if checkthisupdate(database[file]) :  # exit if already present
            continue
     
        files_downloaded += 1
        print('downloading',file, database[file])
        cmd = re.sub('xxxx',file,downloadcmd)
        msg = runcmd(cmd)
        printlist(msg)
    
        with zipfile.ZipFile(file, 'r') as zipp:
            zipp.extractall('.')
       
        os.remove(file)
        print('readresnet', file[:-4])
        msg = runcmd(pdir + '/readresnet.py ' + file[:-4] + ' False')
    
    
    conn = getConnection()
    for  d  in dates:
        with conn.cursor() as cur:
            cur.execute('insert into resnet.version (name, value) values(%s, %s);', ('update', d) )
    conn.commit()
    conn.close


def load_files():
    print('--- files downloaded, loading ---')
    msg = runcmd(pdir + '/create_tables.py  resnet_temp')
    print('create_tables')
    printlist(msg)


def index():

    if files_downloaded == 0:
        print('nothing to index')
        return

    update_nref = """
update resnet.control 
  set num_refs = count 
from
(select count(reference.id) as count, control.id 
   from resnet.reference, resnet.control 
   where reference.id = control.attributes group by control.id)a  
where 
  a.id= control.id;"""

    msg = psql_cmd(update_nref)
    print(msg)

process_files()
load_files()
index()
