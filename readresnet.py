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
import random

#import create_tables

# xml header
xmlheader = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
# tracks total database writes
linesread = 0
# total lines in current release
totalines = 1206676587
# reproducible seed
random.seed('resnetloader')
readversion = True

# fields in reference table
refcolumns  = ['id', 'Authors', 'BiomarkerType', 'CellLineName', 'CellObject', 'CellType', 'ChangeType', 'Collaborator', 'Company', 'Condition', 'DOI',
'EMBASE', 'ESSN', 'Experimental System', 'Intervention', 'ISSN', 'Journal', 'MedlineTA', 'Mode of Action', 'mref','msrc',
'NCT ID', 'Organ', 'Organism', 'Percent', 'Phase', 'Phenotype', 'PII', 'PMID', 'PubVersion', 'PubYear', 'PUI',
'pX', 'QuantitativeType', 'Source', 'Start', 'StudyType', 'TextMods', 'TextRef', 'Tissue', 'Title', 'TrialStatus', 'URL']


# make refmapper
def makerefmap():
    result = {}
    count = 0
    for ref in refcolumns:
        result[ref] = count
        count += 1

    return result

# make reference array, return an array
def makeref(refhash):
    result = ['']*len(refcolumns)
    result[0] = refhash
    return result

# return an array in the "correct" order from the
# reference dictionary
def dictToArray(dic):
    result = []
    for i in refcolumns:
        ref = dic[i]
        result.append(ref)

    return result        


# refmap is map of reference items a map of item, index in array
refmap = makerefmap()

def parseVersion(xml):
    """ write version records to version table """
    sql = 'insert into resnet.version (name,value) values (%s,%s);'
    doc = ElementTree(ET.fromstring(xml))
    with open('version.table','w') as f:
        h = doc.findall('.//attr')
        for h in h:
            name = h.get('name')
            value = h.get('value')
            val = (name, value)
            print ( 'name:%s\tval:%s' % val )
            versioncache.write(val, f) 
    
def indexAttribute(attr):
    # attr is an XML document
    name  = attr.get('name')
    value = attr.get('value')
    index = attr.get('index')
    
    hcode = myhash(name + '|' + value)
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

        for attr in doc.findall('./properties/attr'):
            val = indexAttribute(attr)
            resnetHashes.append(val[0])
            # keep those attributes connected to resnet properties

            hcode1, name1, value1, index1 = val 
            resnetAttributes.append( (hcode1, name1, value1) )
        # add to list to store in attr table    
        attributes += resnetAttributes 

    nodeLocalId = {}
    for node in doc.findall('./nodes/node'): # node
        nodeRef = []
        urn = node.get('urn')
        local_id = node.get('local_id')
        nodehash = myhash(urn)
        nodeLocalId[local_id] = nodehash
        nodeName = ''
        nodeType = ''

        for nodeattr in node.findall('./attr'):
            val = indexAttribute(nodeattr)
            if val[1] ==  'Name':
                nodeName = val[2]
            elif val[1] ==  'NodeType':
                nodeType = val[2]
            else:
                hcode1, name1, value1, index1 = val 
                attributes.append( (hcode1, name1, value1) )
                nodeRef.append(hcode1)

        thisnode = (nodehash, urn, nodeName, nodeType, nodeRef )
        nodes.append(thisnode)


    controlHashes = []

    for control in doc.findall('./controls/control'): # controls
        inref = []
        outref = []
        inoutref = []
        controlType = ''
        ontology = ''
        relationship = ''
        mechanism = ''
        effect = ''

        for controllink in control.findall('./link'): # links
          ref = controllink.get('ref')
          ty =  controllink.get('type')

          if ty == 'in':
            inref.append(nodeLocalId[ref])
          elif ty == 'out':
            outref.append(nodeLocalId[ref])
          elif ty == 'in-out':
            inoutref.append(nodeLocalId[ref])
          else:
            print('*****  unknown link type found:', ty)

        #refhash = myhash( str(inref, outref, inoutref) + str(random.random())
        refhash = -1
        # tried using xml of the control for this snippet but generating the XML is very slow.
        # in some cases there may be more than one  for in and out
        # however these may be only for the lipidomics project.  If required
        # the data type could be arrays instead of integers
        localrefs = []

        for controlattr in control.findall('./attr'): #attributes of the control
            hcode, name, value, index = indexAttribute(controlattr)
            # these are specific to the control, and not to any indivitual references
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
                    if index is None:
                        index = 1

                    idx = int(index) # index is an attribute of the control that says which reference
                                     # it belongs to
                    # expand list to fit index
                    if idx > len(localrefs):
                         for x in range(idx - len(localrefs)):
                            ref_array = makeref(refhash) # array of items for the source reference
                                                   # refhash is the hash id for this relationship
                            localrefs.append(ref_array)  # add to list of references for this relationship

                    xref = localrefs[idx-1]  # get the relevant ref; idx is 1 based, ref is 0 based. 
                    xref[refmap[name]] = value  

                except Exception as e:
                    #pass
                    #traceback.print_exc()
                    print('error',hcode, name, value, index, localrefs )
            
        # end of loop over attributes 
        # use the absolute references for hash, not 'local' to enable combining unique controls
        chash = myhash(str((inref, inoutref, outref, controlType, ontology, relationship, effect, mechanism)))
        c = (chash, inref, inoutref, outref, controlType, ontology, relationship, effect, mechanism, chash)
        #assign non-unique hashes for s 
        # now localrefs is an array of arrays, where we we need an array of tuples
        # 
        for i,x in enumerate(localrefs):
            x[0] = chash
            localrefs[i] = tuple(x)

        for x in localrefs:
            references.append(x)

        # end of this control
        #     
        # use the absolute references for hash, not 'local' to enable combining unique controls

        controlHashes.append(chash)
        controls.append(c)

    # end of loop over controls
    if isPath:
        phash = myhash( str((refhash, rname, rtyp, rurn, resnetHashes, controlHashes)) )
        p  = (phash, rname, rtyp, rurn, resnetHashes, controlHashes)
        pathways.append(p)

    # final  return 
    return  attributes, nodes, controls, references, pathways



def readfile(fname):

    global linesread
    print('\nreading file', fname)

    count = 0
    with open(fname,'r') as f:

        if readversion:
            print('version info:')
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

    with open('reference.table', 'a') as f:  # references is an array of arrays
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
    LINES = 1000000 # lines between status updates

    for line in f:
        linesread += 1
        if line is None:
            return None

        if linesread % LINES == 0:
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
    global readversion
    fname = sys.argv[1]
    if len(sys.argv) > 2 and len(sys.argv[2]) > 0:
        char = (sys.argv[2].lower())[0]
        readversion = char in ('t', '1' ) 
        print('readversion set to:', readversion)

    readfile(fname) 


main()
