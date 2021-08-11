#!/bin/python3
#
# this is designed to run from the RMC version directory, e.g. 201857.
# it further assumes that the loader information is in a directory ../loader from
# that directory

import os
import sys
import fileinput
import random
import psutil

DELIMITER = '\x07'

def dedup(fname, randcrit):
    print('deduplicating', fname)
    cache = set() 
    newname = fname + '.dedup'
    linecount = 0 
    writecount = 0
    errorcount = 0
    startsize = os.path.getsize(fname)
    dups = 0
    with open(newname, 'w') as outfile:
        with open(fname, 'r') as f:
            for line in f:
                linecount += 1

                if linecount % 10000 == 0:
                    pmem = float(psutil.virtual_memory().percent)
                    if pmem > 60:
                        for i in range(200000):
                            cache.pop()
                try:
                    index = int(line.split(DELIMITER)[0])
                    if not index in cache:
                        if random.random() < randcrit:
                            cache.add(index)
                        outfile.write(line)
                        writecount += 1
                    else:
                        dups += 1
        
                except:
                    errorcount += 1
                    print('error at line',linecount, 'skipping:')
                    print(line)

   
    endsize = os.path.getsize(newname) 
    print(fname, ' tracked unique values:', len(cache), 'errors:', errorcount )
    print('old size', startsize, 'new size', endsize, ' diff ', startsize-endsize)
    print('removed', dups, 'duplicate lines, wrote',writecount)
    return newname 


def attrdedup():
	cycles = 10
	randcrit = 0.8
	
	for i in range(cycles):
	    print('dedup cycle', i+1, 'of', cycles)
	    dedup('attr.table.dedup', randcrit)
	    os.rename('attr.table.dedup.dedup', 'attr.table.dedup')
	   
	print('done') 
