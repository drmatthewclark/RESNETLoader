#!/bin/python3
#
# this is designed to run from the RMC version directory, e.g. 201857.
# it further assumes that the loader information is in a directory ../loader from
# that directory

# owner of database or db to connect to
dbname='mclark'

import psycopg2 as psql
import re
import os
import sys
import fileinput
import os
import dbconnect
import subprocess
from dbconnect import getConnection

tables = ['node', 'control', 'pathway', 'attr' ]

dedupcmd = "sort -T `pwd` --field-separator=$\'\\x07\' --key=1,1 -u xxxx_temp  > xxxx.dedup;  rm xxxx_temp"
reversecmd = "tac xxxx  > xxxx_temp"
schema = 'resnet_temp'  # default schema
pdir = os.path.dirname(os.path.realpath(__file__)) # dir of this program

def runcmd(cmd):
    """ run a command and get output"""
    result = []
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        result.append(line.decode('utf8').strip())
    retval = p.wait()

    resultstring = ''
    for i in result:
        resultstring += i + '\n'

    return resultstring


def dedup(fname):

    print('deduplicating',fname)
    lcmd = re.sub('xxxx', fname, dedupcmd)
    rev  = re.sub('xxxx', fname, reversecmd)

    os.system(rev)
    os.system(lcmd)


 
def initdb():
    """ initialize db """

    drop = "drop schema " + schema  + " cascade"
    sql = """
    create schema xxxx;
    create table  xxxx.version(name text, value text);
    create table  xxxx.attr( id bigint, name text, value text);
    create table  xxxx.node( id bigint, urn text, name text, nodetype text, attributes bigint[]);

    create table  xxxx.control(id bigint, inkey bigint[], inoutkey bigint[], outkey bigint[], controltype text,
        ontology text, relationship text, effect text, mechanism text, attributes bigint);

    create table xxxx.pathway(id bigint, name text, type text, urn text, attributes bigint[], controls bigint[]);

    create table xxxx.reference ( id bigint,
       Authors text, BiomarkerType text, CellLineName text, CellObject text, CellType text, ChangeType text, Collaborator text, Company text, Condition text,
       DOI text, EMBASE text, ESSN text, Experimental_System text, Intervention text, ISSN text, Journal text, MedlineTA text, Mode_of_Action text,
       mref text, msrc text, NCT_ID text, Organ text, Organism text, Percent text, Phase text, Phenotype text, PII text, PMID text, PubVersion text, PubYear integer, PUI text,
       pX float, QuantitativeType text, Source text, Start text, StudyType text, TextMods text, TextRef text, Tissue text, Title text, TrialStatus text, URL text);
    """

    sql = re.sub('xxxx', schema, sql)
    conn = getConnection()

    print('initializing schema')
    try:
        print('execute', drop)
        with conn.cursor() as cur:
         cur.execute(drop)
         conn.commit()
    except:
        print('schema did not exist')
        conn.commit() 

    with conn.cursor() as cur:
        for line in sql.split(';'):
           if line.strip() != '':
              print(line)
              cur.execute(line)
              conn.commit()


def indexdb():

    # create indices """
    with open(pdir  + '/' + schema + '.sql', 'r') as sf:
        sql = sf.read()

    conn = getConnection()

    with conn.cursor() as cur:
        statements = sql.split(';')
        for statement in statements:
            if statement.strip() != '' and not statement.startswith('--'):
                print(statement)
                cur.execute(statement)
                conn.commit()    

    conn.commit()    
    conn.close()



def combine_temp():
    """ combine temporary tables with main database """
    conn = getConnection()
    tables = ['attr', 'node', 'control', 'pathway', 'reference' ]

    lschema = re.sub('_temp','',schema)

    for table in tables:
        sql = 'insert into ' + lschema + '.' + table + ' select * from ' + schema + '.' + table + ' on conflict do nothing '
        print(sql)
        with conn.cursor() as cur:
            cur.execute(sql)
            print(cur.rowcount, ' rows inserted ')

    conn.commit()
    conn.close()


     
def load():

    """ load tables.  the only feasible way for tables this large is ti  use the copy command"""

    copycmd1 = "psql -c \"\copy " + schema + ".xxxx from 'xxxx.table.dedup' with (delimiter E'\x07' ,format csv, quote E'\x01')\""
    copycmd2 = "psql -c \"\copy " + schema + ".xxxx from 'xxxx.table' with (delimiter E'\x07' ,format csv, quote E'\x01')\""

    initdb()

    for t in tables:
        dedup(t + ".table" )

    for t2 in tables:
        print('loading table', t2)
        cmd = re.sub("xxxx",t2,copycmd1)
        print(runcmd(cmd))

    for t2 in ['reference', 'version' ]:
        print('loading table', t2)
        cmd = re.sub("xxxx",t2,copycmd2)
        print(cmd)
        print(runcmd(cmd))
    
    indexdb()

    #combine update with full tables 
    if 'temp' in schema:
        combine_temp()


#
# needs an argument to specify whether this is a load from the bulk file or
# a load from an update
#
if len(sys.argv) <1:
    print(' need schema name resnet for full load or resnet_temp for update')

schema = sys.argv[1]
load()
