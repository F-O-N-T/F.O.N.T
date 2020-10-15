#!/usr/bin/env python
# coding: utf-8

# In[1]:


#!/usr/bin/env python
# coding: utf-8


# In[2]:


from konlpy.tag import Kkma
from konlpy.utils import pprint
from collections import Counter


# In[3]:


import sqlite3
from sqlite3 import OperationalError


# In[4]:


def debug_print(args, **kargs):
    #print(args, **kargs)
    pass


# In[5]:


class WordDB:
    #wrapper class for sqlite3
    #with WordDB('dbname.db') as db:
    #    db.get()
    #    db.update(['word1', 'word2', 'word3' ...])
    def __init__(self, filename=''):
        self.__conn = None
        self.__cursor = None
        if(filename):
            try:
                self.create(filename)
            except sqlite3.OperationalError:
                self.conn(filename)
        
    def __enter__(self):
        return self
    
    def __exit__(self, e_type, e_value, tb):
        self.close()
    
    def create(self, filename):
        self.__conn = sqlite3.connect(filename)
        self.__cursor = self.__conn.cursor()
        self.__cursor.execute('''CREATE TABLE WORDLIST
                                (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT NOT NULL)''')
        self.__conn.commit()

    def conn(self, filename):
        self.__conn = sqlite3.connect(filename)
        self.__cursor = self.__conn.cursor()

    def get(self):
        self.__cursor.execute("SELECT id, word FROM WORDLIST")
        return self.__cursor.fetchall()
    
    def update(self, wordlist):
        for word in wordlist:
            self.__cursor.execute("INSERT INTO WORDLIST (word) VALUES (?)", (word, ))
        self.__conn.commit()

    def close(self):
        self.__conn.close()
        self.__conn = None
        self.__cursor = None


# In[1]:


class FONTBagOfWord:
    #bag = FONTBagOfWord()
    #bag.from_file('filename.db')
    #bag.to_file('filename.db')
    #bag.updated()
    #bag.process('some contents you want to analyze')
    #len(bag), print(bag)
    #bag.get(3)
    #bag['word']
    def __init__(self):
        self.__kkma = Kkma()
        self.__word_db = WordDB()
        self.__accepted = ['NNG','NNP','NP','VV','VA', 'OH'] #set the korean tags to read
        self.__wordvec_index = {} #wdictionary of wordvec with its index {index:wordvec}
        self.__wordvec_dict = {} #wdictionary of wordvec with its index {wordvec:index}
        self.__new_words = []
        self.__updated = False
        
    def __del__(self):
        try:
            self.__word_db.close()
        except:
            pass
    
    def from_file(self, filename='')->None:
        if(not filename):
            return
        try:
            self.__word_db.create(filename)
        except:
            self.__word_db.conn(filename)
        try:
            for col in self.__word_db.get():
                self.__wordvec_index[col[0]]=col[1] #(index to word)
                self.__wordvec_dict[col[1]]=col[0] #(word to index)
        finally:
            self.__word_db.close()
    
    def to_file(self, filename):
        self.__word_db.conn(filename)
        self.__word_db.update(self.__new_words)
        self.__new_words = []
        self.__updated = False
        self.__word_db.close()
    
    def updated(self)->bool:
        return self.__updated
    
    def __repr__(self):
        return 'font_bag_of_word(len=' + str(len(self)) +')'
    
    def __getitem__(self, i):
        #exceptions will be handled from the list __wordvec
        if type(i) == str:
            return self.__wordvec_dict[i]
        else:
            raise IndexError("FONTBagOfWord index out of range")

    def get(self, i):
        if type(i) == int:
            return self.__wordvec_index[i]
        else:
            return self[i]
    def __len__(self):
        return len(self.__wordvec_dict)
    
    def process(self, src='')->(list,list):
        indexvec = []
        freqvec = []
        src = src.replace('"', '')
        src = src.replace("'", "")
        article_headers=['(서울=연합뉴스)','[서울=뉴시스]','[파이낸셜뉴스]','(서울=뉴스1)']
        article_footers=['공감언론 뉴시스가 독자 여러분의 소중한 제보를 기다립니다. 뉴스 가치나 화제성이 있다고 판단되는 사진 또는 영상을 뉴시스 사진영상부(n-photo@newsis.com)로 보내주시면 적극 반영하겠습니다.<ⓒ 공감언론 뉴시스통신사. 무단전재-재배포 금지>',
                         '무단전재 및 재배포금지','무단 전재-재배포 금지','<ⓒ경제를 보는 눈, 세계를 보는 창 아시아경제 무단전재 배포금지>'
                         '뉴스1코리아()',
                         "<저작권자 ⓒ '성공을 꿈꾸는 사람들의 경제 뉴스' 머니S, 무단전재 및 재배포 금지>"]
        for i in article_headers:
            src = src.replace(i, '')
        for i in article_footers:
            src = src.replace(i, '')
        
        #divide by tags using kkma engine in koNLPy module
        pos = self.__kkma.pos(src)
        debug_print(pos)
        #accept only NNG(common nouns), NNP(proper nouns), NP(pronoun), VV(verb), VA(adj.)
        pos = [i for i in pos if i[1] in self.__accepted]
        debug_print(pos)
        #get (at most) 200s of most commonly used words
        cnt = Counter(pos).most_common(200)
        
        for i in cnt:
            word_to_search = i[0][0]
            #word_tag = i[0][1]
            word_cnt = i[1]
            word_index = 0
            try:
                word_index = self.__wordvec_dict[word_to_search]
            except KeyError:
                self.__wordvec_index[len(self.__wordvec_dict)] = word_to_search
                self.__wordvec_dict[word_to_search] = len(self.__wordvec_dict)
                word_index = self.__wordvec_dict[word_to_search]
                self.__new_words.append(word_to_search)
                self.__updated = True
            indexvec.append(word_index)
            freqvec.append(word_cnt)
        return indexvec, freqvec


# In[2]:


def test_kkma_konlpy():
    kkma = Kkma()
    while True:
        src = input()
        if src == '':
            break
        pos = kkma.pos(src)
        print(pos)


# In[3]:


def test_font_bag_of_word(filename = ''):
    bag = FONTBagOfWord()
    bag.from_file(filename)
    while True:
        src = input()
        if(src == ''):
            break
        result = bag.process(src)
        print(result)
    print(bag)
    for i in bag:
        print(i, end=' ')
    bag.to_file(filename)


# In[4]:


if __name__ == '__main__':
    pass
    test_kkma_konlpy()
    test_font_bag_of_word('word.db')


# In[ ]:




