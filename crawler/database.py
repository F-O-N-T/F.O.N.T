#!/usr/bin/env python
# coding: utf-8

# In[1]:


import sqlite3
from abc import *
import json


# In[2]:


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
                                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                 title TEXT NOT NULL,
                                 date TEXT NOT NULL,
                                 contents TEXT NOT NULL,
                                 category TEXT,
                                 url TEXT NOT NULL UNIQUE
                                 )''')
        self.__conn.commit()
    
    def conn(self, filename):
        self.__filename = filename
        self.__conn = sqlite3.connect(filename)
        self.__cursor = self.__conn.cursor()

    def get(self, _id='', category='', url=''):
        if _id:
            self.__cursor.execute("SELECT * FROM ARTICLE WHERE id=?", (_id,))
        elif category:
            self.__cursor.execute("SELECT * FROM ARTICLE WHERE category=?",(category,))
        elif url:
            self.__cursor.execute("SELECT * FROM ARTICLE WHERE url=?", (url,))
        else:
            self.__cursor.execute("SELECT * FROM ARTICLE")
        ret = self.__cursor.fetchall()
        for r in range(len(ret)):
            ret[r] = {'id':ret[r][0],
                      'title':ret[r][1],
                      'date':ret[r][2],
                      'contents':ret[r][3],
                      'category':ret[r][4],
                      'url':ret[r][5]}
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
                      'url':ret[r][5]}
        return ret

    def update(self, title, date, contents, category, url):
        
        self.__cursor.execute('INSERT INTO ARTICLE (title, date, contents, category, url) VALUES (?,?,?,?,?)', 
                                 (title, date, contents, category, url))
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

