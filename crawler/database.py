#!/usr/bin/env python
# coding: utf-8

# In[1]:


import sqlite3
from abc import *


# In[2]:


class ArticleDB:
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
        self.__conn = sqlite3.connect(filename)
        self.__cursor = self.__conn.cursor()

    def get(self, category='', url=''):
        if category:
            self.__cursor.execute("SELECT * FROM ARTICLE WHERE category=?",(category,))
        elif url:
            self.__cursor.execute("SELECT * FROM ARTICLE WHERE url=?", (url,))
        self.__cursor.execute("SELECT * FROM ARTICLE")
        return self.__cursor.fetchall()

    def get_random(self, cnt):
        self.__cursor.execute("SELECT * FROM ARTICLE ORDER BY RANDOM() LIMIT ?",(cnt,))
        return self.__cursor.fetchall()

    def update(self, article):
        
        self.__cursor.execute('INSERT INTO ARTICLE (title, date, contents, category, url) VALUES (?,?,?,?,?)', 
                                 (article[0],article[1],article[2],article[3],article[4]))
        self.__conn.commit()

    def close(self):
        self.__conn.close()
        self.__conn = None
        self.__cursor = None


# In[ ]:




