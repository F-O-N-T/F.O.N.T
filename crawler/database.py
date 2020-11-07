#!/usr/bin/env python
# coding: utf-8

# In[1]:


import sqlite3
from abc import *
import json


# In[2]:


class Article:
    def __init__(self, title, date, contents, category1, category2, paper, url):
        self.title = title
        self.date = date
        self.contents = contents
        self.category1 = category1
        self.category2 = category2
        self.paper = paper
        self.url = url

class ArticleDB:
    def __init__(self, filename=''):
        self.__conn = None
        self.__cursor = None
        self.__filename = filename
        if(filename):
            try:
                self.create(filename)
            except sqlite3.OperationalError:
                self.conn(filename)

    def __enter__(self):
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        self.close()

    def create(self, filename):
        self.__conn = sqlite3.connect(filename)
        self.__cursor = self.__conn.cursor()
        self.__cursor.execute('''CREATE TABLE ARTICLE
                                (Id INTEGER PRIMARY KEY AUTOINCREMENT,
                                 Title TEXT,
                                 Date VARCHAR(20),
                                 Contents TEXT,
                                 Category1 VARCHAR(8),
                                 Category2 VARCHAR(8),
                                 Paper VARCHAR(10),
                                 URL TEXT NOT NULL UNIQUE
                                 )''')
        self.__conn.commit()
    
    def conn(self, filename):
        self.__filename = filename
        self.__conn = sqlite3.connect(filename)
        self.__cursor = self.__conn.cursor()

    def get(self, _id='', category='', url=''):
        if _id:
            self.__cursor.execute("SELECT * FROM ARTICLE WHERE Id=?", (_id,))
        elif category:
            #FIXME: CATEGORY IS A SET OF COMMON CATEGORIES, NOT COMMON CATEGORY & DETAILED CATEGORY
            self.__cursor.execute("SELECT * FROM ARTICLE WHERE Category1=?",(category,))
        elif url:
            self.__cursor.execute("SELECT * FROM ARTICLE WHERE URL=?", (url,))
        else:
            self.__cursor.execute("SELECT * FROM ARTICLE")
        ret = self.__cursor.fetchall()
        for r in range(len(ret)):
            ret[r] = {'id':ret[r][0],
                      'title':ret[r][1],
                      'date':ret[r][2],
                      'contents':ret[r][3],
                      'category':ret[r][4],
                      'Category1':ret[r][4],
                      'Category2':ret[r][5],
                      'paper': ret[r][6],
                      'url':ret[r][7]}
        return ret

    def get_random(self, cnt):
        self.__cursor.execute("SELECT * FROM ARTICLE ORDER BY RANDOM() LIMIT ?",(cnt,))
        ret = self.__cursor.fetchall()
        for r in range(len(ret)):
            ret[r] = {'id':ret[r][0],
                      'title':ret[r][1],
                      'date':ret[r][2],
                      'contents':ret[r][3],
                      'category':ret[r][4],
                      'Category1':ret[r][4],
                      'Category2':ret[r][5],
                      'paper': ret[r][6],
                      'url':ret[r][7]}
        return ret

    def update(self, title, date, contents, category1, category2, paper, url):
        
        self.__cursor.execute('INSERT INTO ARTICLE (Title, Date, Contents, Category1, Category2, URL) VALUES (?,?,?,?,?,?)', 
                                 (title, date, contents, category1, category2, paper, url))
        self.__conn.commit()

    def close(self):
        self.__conn.close()
        self.__conn = None
        self.__cursor = None


# In[5]:


class ArticleVectorDB:
    def __init__(self, filename=''):
        self.__conn = None
        self.__cursor = None
        self.__filename = filename
        if(filename):
            try:
                self.create(filename)
            except sqlite3.OperationalError as e:
                self.conn(filename)

    def __enter__(self):
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        self.close()

    def create(self, filename):
        self.__conn = sqlite3.connect(filename)
        self.__cursor = self.__conn.cursor()
        self.__cursor.execute('''CREATE TABLE ARTICLEVECTOR
                                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                 version INTEGER,
                                 vector TEXT,
                                 a_id INTEGER,
                                 FOREIGN KEY(a_id) REFERENCES ARTICLE(id)
                                 )''')
        self.__conn.commit()
    
    def conn(self, filename):
        self.__filename = filename
        self.__conn = sqlite3.connect(filename)
        self.__cursor = self.__conn.cursor()

    def get(self, a_id='', url='',version=None):
        if a_id and version:
            self.__cursor.execute("SELECT * FROM ARTICLEVECTOR WHERE a_id=? AND version=?", (a_id, version))
        elif a_id:
            self.__cursor.execute("SELECT * FROM ARTICLEVECTOR WHERE a_id=?", (a_id,))
        elif url:
            self.__cursor.execute("SELECT * FROM ARTICLE WHERE url=?", (url,))
            one = self.__cursor.fetchone()
            if one is None:
                return None
            self.__cursor.execute("SELECT * FROM ARTICLEVECTOR WHERE a_id=?", (one[0],))
        else:
            self.__cursor.execute("SELECT * FROM ARTICLEVECTOR")
        ret = self.__cursor.fetchone()
        if ret is None:
            return None
        if ret[2] == '' or ret[2] == ' ':
            data = ([],[])
        else:
            data = list(map(int, ret[2].split(' ')))
            assert len(data) % 2 == 0
            data = (data[:len(data)//2], data[len(data)//2:])
        ret = {'id':ret[0],'version':ret[1],'data':data,'a_id':ret[3]}
        return ret

    def get_random(self, cnt):
        #get random number of vectors
        self.__cursor.execute("SELECT * FROM ARTICLEVECTOR ORDER BY RANDOM() LIMIT ?",(cnt,))
        ret = []
        for i in self.__cursor.fetchall():
            if i[2] == '' or i[2] == ' ':
                data = ([],[])
            else:
                data = list(map(int, i[2].split(' ')))
                assert len(data) % 2 == 0
                data = (data[:len(data)//2], data[len(data)//2:])
            ret.append({'id':i[0],'version':i[1],'data':data,'a_id':i[3]})
        return ret

    def update(self, a_id, version, index, freq):
        #remove old data(equal same with lower version), keep(or create) concurrent data
        self.__cursor.execute("SELECT * FROM ARTICLEVECTOR WHERE a_id=? and version=?", (a_id,version))
        one = self.__cursor.fetchone()
        if one:
            return
        for i in self.__cursor.execute("SELECT * FROM ARTICLEVECTOR WHERE a_id=?", (a_id,)):
            self.__cursor.execute("DELETE FROM ARTICLEVECTOR WHERE a_id=? and version=?", (i[0], i[1]))
            
        self.__cursor.execute('INSERT INTO ARTICLEVECTOR (a_id, version, vector) VALUES (?,?,?)', 
                                 (a_id,version, ' '.join(map(str, index)) + ' ' + ' '.join(map(str, freq)) ) )
        self.__conn.commit()

    def close(self):
        self.__conn.close()
        self.__conn = None
        self.__cursor = None

