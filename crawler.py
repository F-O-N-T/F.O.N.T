#!/usr/bin/env python
# coding: utf-8

# In[16]:


from Algorithm.tags import FONTBagOfWord, WordDB
from crawler.database import ArticleDB, ArticleVectorDB

from crawler.naver_crawler import crawl_naver_newest as crawl
from crawler.naver_crawler import crawl_naver_one as crawl_one
from crawler.naver_crawler import InternalServerError
from sqlite3 import IntegrityError, OperationalError


# In[17]:


WORDDB='words.db'
ARTICLEDB='article.db'
VECDB_VERSION=7


# In[18]:


def run_crawler(num_of_page, debug_print=True):
    
    generator = crawl(num_of_page, return_urls_only=True)
    
    bag = FONTBagOfWord()
    bag.from_file(WORDDB)
    
    count = 0
    count_pass = 0
    count_err = 0
    while True:

        #get list of url of the articles
        try:
            article_url = next(generator)
        except StopIteration:
            break
        except InternalServerError:
            print("Error at list:", article_url)
            count_err += 1
            if(debug_print and count_err % 10 == 0):
                print("countered ", count_err," errors")
            continue
        except Exception as e:
            raise(e)

        #determine if the article is already stored in db
        if(article_url):
            proc=None
            with ArticleDB(ARTICLEDB) as articleDB:
                exists = articleDB.get(url=article_url)
            #the article does not exists in db
            if not exists:
                try:
                    article = crawl_one(article_url)
                #the article does not exists in db, but some internal error occured 
                except InternalServerError as e:
                    print("Error at article:", article)
                    count_err += 1
                    if(debug_print and count_err % 10 == 0):
                        print("countered ", count_err," errors")
                    continue

                #the article does not exists in db, and some unknown error occured
                except Exception as e:
                    raise(e)

                proc = bag.process(article['contents'])
                bag.to_file(WORDDB)
                vec = (proc,article)
            #the article already exists in db
            else:
                count_pass += 1
                if(debug_print and count_pass % 10 == 0):
                    print("passed ", count_pass," articles")
                continue


            #determine if the article is valid, meaning it contains korean and no error occured yet.
            #and store the article onto database.
            if(vec and vec[0] and vec[0][0] and vec[0][1]):
                try:
                    with ArticleDB(ARTICLEDB) as articleDB:
                        articleDB.update(article['title'], article['date'], article['contents'], article['category'], article['url'])
                        a_id = articleDB.get(url=article['url'])[0]['id']
                    with ArticleVectorDB(ARTICLEDB) as articleVectorDB:
                        articleVectorDB.update(a_id, VECDB_VERSION, proc[0], proc[1])
                except IntegrityError:
                    continue
                else:
                    count = count + 1
                    if(count % 10 == 0):
                        print("got " + str(count) + " articles")


# In[19]:


if __name__ == "__main__":
    n_page = int(input("number of page to crawl:"))
    run_crawler(n_page, debug_print=True)


# In[ ]:




