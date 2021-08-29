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
from cachingwriter import CachingWriter
import traceback


#import create_tables

# xml header
xmlheader = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
# tracks total database writes
linesread = 0
# total lines in current release
totalines = 1206676587

# fields in reference table
refitems = ['id', 'Authors', 'BiomarkerType', 'CellLineName', 'CellObject', 'CellType', 'ChangeType', 'Collaborator', 'Company', 'Condition', 'DOI',
'EMBASE', 'ESSN', 'Experimental System', 'Intervention', 'ISSN', 'Journal', 'MedlineTA', 'Mode of Action', 'mref','msrc',
'NCT ID', 'Organ', 'Organism', 'Percent', 'Phase', 'Phenotype', 'PII', 'PMID', 'PubVersion', 'PubYear', 'PUI',
'pX', 'QuantitativeType', 'Source', 'Start', 'StudyType', 'TextMods', 'TextRef', 'Tissue', 'Title', 'TrialStatus', 'URL']


# make refmapper
def makerefmap():
    result = {}
    count = 0
    for item in refitems:
        result[item] = count
        count += 1

    return result

# make reference array
def makeref():
    return ['']*len(refitems)

# return an array in the "correct" order from the
# reference dictionary
def dictToArray(dic):
    result = []
    for i in refitems:
        item = dic[i]
        result.append(item)

    return result        

refmap = makerefmap()

def parseVersion(xml):
    """ write version records to version table """
    sql = 'insert into resnet.version (name,value) values (%s,%s);'
    doc = ElementTree(ET.fromstring(xml))
    with open('version','w') as f:
        h = doc.findall('.//attr')
        for hitem in h:
            name = hitem.get('name')
            value = hitem.get('value')
            val = (name, value)
            print ( 'name:%s\tval:%s' % val )
            versioncache.write(val, f) 
    
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
    references = []

    if rname is not None:  # to handle pathway nodes.
        isPath = True
        rtyp = e.get('type')
        # if not a pathway bail out early
        if rtyp != 'Pathway':
            return  attributes, nodes, controls, [], pathways
            
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
        nodeName = ''
        nodeType = ''

        for hitem in item.findall('./attr'):
            val = indexAttribute(hitem)
            if val[1] ==  'Name':
                nodeName = val[2]
            elif val[1] ==  'NodeType':
                nodeType = val[2]
            else:
                attributes.append(val)
                hcode = val[0]
                nodeRef.append(hcode)

        node = (nodehash, urn, nodeName, nodeType, nodeRef )
        nodes.append(node)

    controlHashes = []
    for item in doc.findall('./controls/control'): # controls
        inref = []
        outref = []
        inoutref = []
        controlType = ''
        ontology = ''
        relationship = ''
        mechanism = ''
        effect = ''
        # in some cases there may be more than one item for in and out
        # however these may be only for the lipidomics project.  If required
        # the data type could be arrays instead of integers
        for fitem in item.findall('./link'): # links
          ref = fitem.get('ref')
          ty =  fitem.get('type')
          if ty == 'in':
            inref.append(nodeLocalId[ref])
          elif ty == 'out':
            outref.append(nodeLocalId[ref])
          elif ty == 'in-out':
            inoutref.append(nodeLocalId[ref])
          else:
            print('*****  unknown link type:', ty)

        ref = makeref()
        setavalue = False
        rhash = myhash(str(item)) # hash for this control
        localrefs = []

        for gitem in item.findall('./attr'): #attributes of the control
            hcode, name, value, index = indexAttribute(gitem)

            if name ==  'ControlType':
                controlType = value
            elif name ==  'Ontology':
                ontology = value
            elif name ==  'Relationship':
                relationship = value
            elif name ==  'Effect':
                effect = value
            elif name ==  'Mechanism':
                mechanism = value
            else:
                try:
                    if index is not None:
                        idx = int(index)
                    else:
                        idx = 1 # pretend we have one if missing, which happens when there
                                # is only 1 reference in some cases

                    if idx > len(localrefs):
                         for x in range(idx - len(localrefs)):
                            localrefs.append(makeref())

                    ref = localrefs[idx-1]
                    ref[0] = rhash
                    # use this mechanism instead of dict to
                    # insure the order
                    ref[refmap[name]] = value  
                    localrefs[idx-1] = ref
                    setavalue = True
                except Exception as e:
                    traceback.print_exc()
                    print('error', e)
                    print('error',hcode, name, value, index, localrefs )
            
        # end of loop over attributes 
        #assign non-unique hashes for items 
        # now localrefs is an array of arrays, where we we need an array of tuples
        # 
        for i,xitem in enumerate(localrefs):
            localrefs[i] = tuple(xitem)

        if  setavalue: 
            for xitem in localrefs:
                references.append(xitem)
        else:
            rhash = ''

        # end of this control
        #     
        # use the absolute references for hash, not 'local' to enable combining unique controls
        chash = myhash(str((inref, inoutref, outref, rhash)))
        c = (chash, inref, inoutref, outref, controlType, ontology, relationship, effect, mechanism, rhash)

        controlHashes.append(chash)
        controls.append(c)

    # end of loop over controls
    if isPath:
        phash = myhash( str((rhash, rname, rtyp, rurn, resnetHashes, controlHashes)) )
        p  = (phash, rname, rtyp, rurn, resnetHashes, controlHashes)
        pathways.append(p)

    # final  return 
    return  attributes, nodes, controls, references, pathways



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
        attrcache.stats()
        controlcache.stats()
        refcache.stats()
        nodecache.stats()
        pathcache.stats()

versioncache = CachingWriter('version', False)
attrcache    = CachingWriter('attr')
controlcache = CachingWriter('control')
refcache = CachingWriter('reference', False) # no caching
nodecache = CachingWriter('node')
pathcache = CachingWriter('pathway')

def precord(record):
    """ parse record and create db records """

    attributes, nodes, controls, references, pathways  = parseResnet(record)

    with open ('control.table', 'a') as f:
        for i in controls:
            controlcache.write(i, f)

    with open('references.table', 'a') as f:  # references is an array of arrays
        for i in references:
            refcache.write(i, f)

    with open('attr.table', 'a') as f:
        for i in attributes:
            attrcache.write(i, f)

    with open ('node.table', 'a') as f:
        for i in nodes:
            nodecache.write(i, f)

    with open ('pathway.table', 'a') as f:
        for i in pathways:
            pathcache.write(i, f)



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

        if linesread % 500000 == 0:
            elapsed = timer() - start
            fractiondone = linesread/totalines
            totaltime = (elapsed*totalines/linesread)
            time_to_complete = totaltime - elapsed

            delta = str(timedelta(seconds=time_to_complete))[:-7]
            total = str(timedelta(seconds=totaltime))[:-7]

            print('%9d lines %6.3f%% elapsed %s end in %s total time %s' % 
                (linesread, 100*fractiondone, str(timedelta(seconds=elapsed))[:-7], delta, total ))
 
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
    #create_tables.create()

main()
