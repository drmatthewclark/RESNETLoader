#
#
import re
import random

class CachingWriter:

    def __init__(self, name, docache=True):
        self.cache =  {}
        self.callcount = 0
        self.writecount = 0
        self.dupsskipped = 0
        self.DELIMITER =  '\x07'  
        self.QUOTE     =  '\x01' 
        self.MAXSIZE  = 20000000 # max size
        self.name = name
        self.fields = 0
        self.docache = docache 

    def stats(self):
        print(self.name, 'cache name')
        print(self.callcount, 'calls')
        print(self.writecount,'records written')
        print(self.dupsskipped, 'records skipped')
        if len(self.cache) > 0:
            maxdup = max(self.cache.values())
            print(maxdup, 'max duplicates of a single record')
        print('')

    def write(self, i, f):

        self.callcount += 1

        if not self.docache:
            self.writedb(i,f)
            return


        idx = i[0]
        if idx in self.cache:
            # count how many times cache items were re-used
            count = self.cache[idx] + 1
            self.cache[idx] = count
            self.dupsskipped += 1
            return
        else:
            self.cache[idx] = 0
            self.writedb(i,f)

        if len(self.cache) > self.MAXSIZE and self.callcount % 500000 == 0:
            self.prunecache()

    def prunecache(self):
        # prune unused keys to make room
        
        dictsize = len(self.cache)
        print(self.name, 'trimming cache', self.dupsskipped, 
          'dups skipped, cache size:', dictsize)

        cache2 = {}
        for (key, item) in self.cache.items():
            # randomlly remove half of the cache lines that have not been duplicated
            if item > 0  or random.random() < 0.5:
               cache2[key] = item 
           
        self.cache.clear() 
        self.cache = cache2
        newsize = len(cache2)
        diff = dictsize - newsize
        print(self.name, 'removed ', diff, 'entries', len(self.cache), 'remain')
        self.stats()

        if newsize/self.MAXSIZE  > 0.80:
            self.MAXSIZE *= 1.1


    def writedb(self,data, f):
        """ write a record the database file """
        self.writecount += 1
        d = ''
        leftbr = self.QUOTE + '{'
        rightbr = '}' + self.QUOTE 

        if self.fields == 0:
            self.fields = len(data)
        else:
            if len(data) != self.fields:
                print('expected',self.fields,'fields but got', len(data))
                print(data)

        for item in data:
    
            sitem = str(item).replace('\n', ' ').rstrip()
    
            if item is None:  # postgres doesn't like this'
               sitem = ''
    
            elif isinstance(item, list): # postgres array is like "{'a', 'b' ... }"
               sitem = re.sub('^\[', leftbr, sitem)
               sitem = re.sub('\]$', rightbr, sitem)
    
            d += sitem + self.DELIMITER
        d = d[:-1] + '\n'  # trim delimiter,add newline
    
        f.write(d)
