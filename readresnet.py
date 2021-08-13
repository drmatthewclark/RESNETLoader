#!/bin/python3 -u
#
# this is designed to run from the RMC version directory, e.g. 201857.
# it further assumes that the loader information is in a directory ../loader from
# that directory


import xml.etree.ElementTree as ET
from   xml.etree.ElementTree import ElementTree
from myhash import myhash
import re
import sys
from timeit import default_timer as timer
from datetime import timedelta
#import create_tables

# xml header
xmlheader = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
# tracks total database writes
linesread = 0
records = 0
# total lines in current release
totalines = 1206676587
DELIMITER =  '\x07'  # char not found in data

def writedb(data, f):
    """ write a record the database """
    global records

    if data is None:
        return

    records += 1

    if records % 200000 == 0:
        elapsed = timer() -start
        fractiondone = linesread/totalines
        time_to_complete = ((elapsed/linesread)*totalines)  - elapsed
        delta = str(timedelta(seconds=time_to_complete))[:-7]
        print('%9d records %9d lines %6.3f%% elapsed %s end in %s' % 
            (records, linesread, 100*fractiondone, str(timedelta(seconds=elapsed))[:-7], delta) )
    
    d = ''
    for item in data:

        sitem = str(item).replace('\n', ' ').rstrip()

        if item is None:  # postgres doesn't like this'
           sitem = ''

        elif isinstance(item, list): # postgres array is like "{'a', 'b' ... }"
           sitem = re.sub('^\[', '"{', sitem)
           sitem = re.sub('\]$', '}"', sitem)

        d += sitem + DELIMITER
    d = d[:-1] + '\n'  # trim delimiter,add newline

    f.write(d)


def parseVersion(xml):
    """ write version records to version table """
    sql = 'insert into resnet.version (name,value) values (%s,%s);'
    doc = ElementTree(ET.fromstring(xml))

    h = doc.findall('.//attr')
    for hitem in h:
        name = hitem.get('name')
        value = hitem.get('value')
        val = (name, value)
        print('name:%s\t  value: %s' % val )
    
def indexAttribute(item):

    name = item.get('name')
    value = item.get('value')
    index = item.get('index')
    
    hcode = myhash(name + '|' + value + '|' + str(index))
    val = (hcode, name, value, index)
    return val 


def parseResnet(xml):
    # cut this big section out
    if '<attachments>' in xml:
        xml = re.sub('<attachments>.*</attachments>','',xml,flags=re.M)

    doc = ElementTree(ET.fromstring(xml))
    nodes      = []
    attributes = []
    controls   = []
    pathways   = []
    isPath     = False

    e = doc.getroot()

    rname = e.get('name')
    resnetAttributes = []

    if rname is not None:  # to handle pathway nodes.
        isPath = True
        rtyp = e.get('type')
        # if not a pathway bail out early
        if rtyp != 'Pathway':
            return  attributes, nodes, controls, pathways
            
        rurn = e.get('urn')
        resnetHashes = []
        rhash = myhash(str((rname, rtyp, rurn)))
        for item in doc.findall('./properties/attr'):
            val = indexAttribute(item)
            resnetHashes.append(val[0])
            # keep those attributes connected to resnet properties
            resnetAttributes.append(val)
        # add to list to store in attr table    
        attributes += resnetAttributes 

    nodeLocalId = {}
    for item in doc.findall('./nodes/node'): # node
        nodeRef = []
        urn = item.get('urn')
        local_id = item.get('local_id')
        nodehash = myhash(urn)
        nodeLocalId[local_id] = nodehash

        for hitem in item.findall('./attr'):
            val = indexAttribute(hitem)
            hcode = val[0]
            nodeRef.append(hcode)
            attributes.append(val)

        node = (nodehash, urn, nodeRef)
        nodes.append(node)

    controlHashes = []
    for item in doc.findall('./controls/control'): # controls
        controlRef = []
        inref = []
        outref = []
        # in some cases there may be more than one item for in and out
        # however these may be only for the lipidomics project.  If required
        # the data type could be arrays instead of integers
        for fitem in item.findall('./link'): # links
          ref = fitem.get('ref')
          ty =  fitem.get('type')
          if ty == 'in' or ty == 'in-out':
            inref.append(nodeLocalId[ref])
          elif ty == 'out':
            outref.append(nodeLocalId[ref])
          else:
            print('*****  unknown link type:', ty)

        for gitem in item.findall('./attr'): #attributes
          val = indexAttribute(gitem)
          hcode = val[0]
          controlRef.append(hcode)
          attributes.append(val)
     
        # use the absolute references for hash, not 'local' to enable combining unique controls
        chash = myhash( str((inref, outref, controlRef)) )
        c = (chash, inref, outref, controlRef)
        controlHashes.append(chash)
        controls.append(c)

    if isPath:
        p  = (rhash, rname, rtyp, rurn, resnetHashes, controlHashes)
        pathways.append(p)

    # final  return 
    return  attributes, nodes, controls, pathways




def readfile(fname):

    global linesread
    print('\nreading file', fname)
    print('version info:')

    count = 0
    with open(fname,'r') as f:
        version = ''
        for line in f:
            linesread += 1
            version += line
            if  "</properties>" in line:
                break
        version += "</batch>"
        parseVersion(version)

        print('\n')

        while True:
            count += 1
            record = readnode(f) 
            if record is None:
                break
            precord(record)

        print("completed")
        print(records, "records")


attrcache = set()
# cache size limit to avoid runnin out of memory
MAXCACHE = 10000000

def tryattrcache(i,f):
    """
    try to identify obvious duplicates early to make deduplication easier later
    """
    idx   = i[0]
    dtype = i[1]
    value = i[2] # value

    if idx in attrcache:
        return

    elif not 'ID' in dtype:
        # if the value is long it is not worth caching
        if len(value) < 256 and len(attrcache) < MAXCACHE:
            attrcache.add(idx)
        else:
            attrcache.pop()

    writedb(i,f)
 

def precord(record):
    """ parse record and create db records """

    attributes, nodes, controls, pathways  = parseResnet(record)

    with open('attr.table', 'a') as f:
        for i in attributes:
            tryattrcache(i,f)

    with open ('node.table', 'a') as f:
        for i in nodes:
            writedb(i, f)


    with open ('control.table', 'a') as f:
        for i in controls:
            writedb(i, f)

    with open ('pathway.table', 'a') as f:
        for i in pathways:
            writedb(i, f)



def readnode(f):
    """ read the next node in the file """
    global linesread
    counter = 0
    result = xmlheader
    ok = False
    for line in f:
        linesread += 1
        if line is None:
            return None

        if not '<resnet' in line and not ok: #spool to resnet  record
            counter += 1
            if counter == 20:
                print('spooled 20 lines without finding <resnet tag')
            continue

        ok = True

        result += line 
        if '</resnet' in line:
            return result



start = timer()




def main(): 

    fname = sys.argv[1]
    readfile(fname) 
    create_tables.create()

main()
