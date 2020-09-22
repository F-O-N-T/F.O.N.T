#!/usr/bin/env python
# coding: utf-8
from konlpy.tag import Kkma
from konlpy.utils import pprint
from collections import Counter

def debug_print(args, **kargs):
    #print(args, **kargs)
    pass
    
class font_bag_of_word:
    def __init__(self):
        self.__accepted = ['NNG','NNP','NP','VV','VA'] #set the korean tags to read
        self.__wordvec = [] #simple list of the words
        self.__wordvec_dict = {} #wdictionary of wordvec with its index {wordvec:index}
        self.__updated = False
        self.__kkma = Kkma()
    
    def from_file(self, filename='')->None:
        pass
    
    def to_file(self, filename):
        pass
        self.__updated = False
    
    def updated(self)->bool:
        return self.__updated
    
    def __repr__(self):
        return 'font_bag_of_word(len=' + str(len(self)) +')'
    
    def __getitem__(self, i:int):
        #exceptions will be handled from the list __wordvec
        return self.__wordvec[i]

    def __len__(self):
        return len(self.__wordvec)
    
    def process(self, string='')->(list,list):
        indexvec = []
        freqvec = []
        #divide by tags using kkma engine in koNLPy module
        pos = self.__kkma.pos(src)
        debug_print(pos)
        #accept only NNG(common nouns), NNP(proper nouns), NP(pronoun), VV(verb), VA(adj.)
        pos = [i for i in pos if i[1] in self.__accepted]
        debug_print(pos)
        #get (at most) 100s of most commonly used words
        cnt = Counter(pos).most_common(100)
        
        for i in cnt:
            word_to_search = i[0][0]
            #word_tag = i[0][1]
            word_cnt = i[1]
            #ignore the words that had been never used, or used only once
            if(word_cnt < 2):
                continue
            
            #update wordvector if needed
            #else, get index of the word and return it with the number of the word used.
            try:
                word_index = self.__wordvec_dict[word_to_search]
            except KeyError:
                self.__wordvec_dict[word_to_search] = len(self.__wordvec_dict)
                word_index = self.__wordvec_dict[word_to_search]
                self.__wordvec.append(word_to_search)
                self.__updated = True
            indexvec.append(word_index)
            freqvec.append(word_cnt)
        return indexvec, freqvec
bag = font_bag_of_word()

for i in range(3):
    result = bag.process(input())
    print(result)

print(bag)
for i in bag:
    print(i)
print(bag)
for i in bag:
    print(i, end=' ')
#should I return the tags to distinguish the synonyms?