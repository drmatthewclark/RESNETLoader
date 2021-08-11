#!/bin/python3
#
# this is designed to run from the RMC version directory, e.g. 201857.
# it further assumes that the loader information is in a directory ../loader from
# that directory

# owner of database or db to connect to
dbname='mclark'
debug = True
noinsert = False  # true for testing without database inserts
checkpointfile = 'resnet.record'
stopfile = 'resnet.stop'

import psycopg2 as psql
import re
import os
import sys
import fileinput
DELIMITER = '\x07'

MAX_CACHE = 50000000

def dedup(fname):
    print('deduplicating', fname)
    newname = fname + '.dedup'
    cache = set() 
    linecount = 0 
    errorcount = 0

    with open(newname, 'w') as outfile:
        with open(fname, 'r') as f:
            for line in f:
                linecount += 1
                try:
                    index = int(line.split(DELIMITER)[0])
                    if not index in cache:
                        if len(cache) < MAX_CACHE:
                            cache.add(index)
                        outfile.write(line)
                except:
                    errorcount += 1
                    print('error at line',linecount, 'skipping:')
                    print(line)

    print(fname, ' had unique values:', len(cache), 'errors:', errorcount )


def initdb():
    """ initialize db """
    drop = "drop schema resnet cascade"
    sql = """
    create schema resnet;
    create table resnet.version(name text, value text);
    create table resnet.attr( id bigint, name text, value text, index integer);
    create table resnet.node( id bigint, urn text, attributes bigint[]);
    create table resnet.control(id bigint, inkey bigint, outkey bigint, attributes bigint[]);
    create table resnet.pathway(id bigint, name text, type text, urn text, attributes bigint[], controls bigint[]);
    create or replace view resnet.nodev as (select node.id, urn, name as type, value from 
        resnet.node, resnet.attr where attr.id = any(node.attributes));
    create or replace view resnet.controlv as (select control.id, i.urn as inkey, o.urn as outkey, 
        name as type, value from 
        resnet.control, resnet.node i, resnet.node o, resnet.attr where i.id = inkey and o.id = outkey 
        and attr.id = any(control.attributes));
    """

    print('initializing schema')
    try:
        with conn.cursor() as cur:
         cur.execute(drop)
         conn.commit()
    except:
        print('schema did not exist')
        conn.commit() 

    with conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()


def indexdb():

    # clean up duplicates left over in attr
    dedup = 'delete from resnet.attr t1 using resnet.attr t2 where t1.id = t2.id and t1.ctid > t2.ctid;'

    # create indices """
    sql = """
             alter table resnet.attr add PRIMARY KEY (id);
             create index on resnet.attr(name);
             create index on resnet.attr(value);
             alter table resnet.node add PRIMARY KEY (id);
             create index on resnet.node(urn);
             alter table resnet.control add PRIMARY KEY(id);
             create index on resnet.control(inkey);
             create index on resnet.control(outkey);
             alter table resnet.pathway add PRIMARY KEY(id);
             create index on resnet.pathway(name);
             create index on resnet.pathway(type);
             create index on resnet.pathway(urn);
            
    """

    with conn.cursor() as cur:
        cur.execute(dedup)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()    

conn = None

def create(): 
    global conn
    conn=psql.connect(user=dbname)    
    tables = ["node", "control", "pathway", "attr" ]
    initdb() 

    for t in tables:
        dedup(t + ".table")            

    copycmd = "psql -c \"\copy resnet.xxxx from 'xxxx.table.dedup' with (delimiter E'\x07' ,format csv, quote E'\x01')\""
    for t in tables:
        print('loading', t)
        cmd = re.sub("xxxx",t,copycmd)
        os.system(cmd)

    indexdb()
   
 
