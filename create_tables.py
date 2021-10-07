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

tables = ['node', 'control', 'pathway', 'attr' ]

dedupcmd = "sort -T `pwd` --field-separator=$\'\\x07\' --key=1,1 -u xxxx_temp  > xxxx.dedup;  rm xxxx_temp"
reversecmd = "tac xxxx  > xxxx_temp"

def dedup(fname):

    print('deduplicating',fname)
    lcmd = re.sub('xxxx', fname, dedupcmd)
    rev  = re.sub('xxxx', fname, reversecmd)

    print(rev)
    os.system(rev)
    print(lcmd)
    os.system(lcmd)


 
def initdb():
    """ initialize db """

    drop = "drop schema resnet cascade"
    sql = """
    create schema resnet;
    create table resnet.version(name text, value text);
    create table resnet.attr( id bigint, name text, value text);
    create table resnet.node( id bigint, urn text, name text, nodetype text, attributes bigint[]);

    create table resnet.control(id bigint, inkey bigint[], inoutkey bigint[], outkey bigint[], controltype text,
        ontology text, relationship text, effect text, mechanism text, attributes bigint);

    create table resnet.pathway(id bigint, name text, type text, urn text, attributes bigint[], controls bigint[]);

    create table resnet.reference ( id bigint,
       Authors text, BiomarkerType text, CellLineName text, CellObject text, CellType text, ChangeType text, Collaborator text, Company text, Condition text,
       DOI text, EMBASE text, ESSN text, Experimental_System text, Intervention text, ISSN text, Journal text, MedlineTA text, Mode_of_Action text,
       mref text, msrc text, NCT_ID text, Organ text, Organism text, Percent text, Phase text, Phenotype text, PII text, PMID text, PubVersion text, PubYear integer, PUI text,
       pX float, QuantitativeType text, Source text, Start text, StudyType text, TextMods text, TextRef text, Tissue text, Title text, TrialStatus text, URL text);
    """

    conn = psql.connect(dbname=dbname)

    print('initializing schema')
    try:
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
    this_path  = os.path.dirname(os.path.abspath(__file__))
    with open(this_path + '/resnet.sql', 'r') as sf:
        sql = sf.read()

    conn = psql.connect(dbname=dbname)

    with conn.cursor() as cur:
        statements = sql.split(';')
        for statement in statements:
            if statement.strip() != '' and not statement.startswith('--'):
                print(statement)
                cur.execute(statement)
                conn.commit()    

    conn.commit()    
    conn.close()


def load():

    """ load tables.  the only feasible way for tables this large is ti  use the copy command"""

    copycmd1 = "psql -c \"\copy resnet.xxxx from 'xxxx.table.dedup' with (delimiter E'\x07' ,format csv, quote E'\x01')\""
    copycmd2 = "psql -c \"\copy resnet.xxxx from 'xxxx.table' with (delimiter E'\x07' ,format csv, quote E'\x01')\""

    initdb()

    for t in tables:
        dedup(t + ".table" )

    for t2 in tables:
        print('loading table', t2)
        cmd = re.sub("xxxx",t2,copycmd1)
        print(cmd)
        os.system(cmd)

    for t2 in ['reference', 'version' ]:
        print('loading table', t2)
        cmd = re.sub("xxxx",t2,copycmd2)
        print(cmd)
        os.system(cmd)
    
    indexdb()

load()
