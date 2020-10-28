#!/usr/bin/env python
# coding: utf-8

# In[1]:


from Algorithm.tags import FONTBagOfWord, WordDB

from crawler.naver_crawler import crawl_naver_newest as crawl
from crawler.naver_crawler import crawl_naver_one as crawl_one
from crawler.naver_crawler import InternalServerError

from crawler.database import ArticleDB, ArticleVectorDB
from sklearn.cluster import MiniBatchKMeans, AgglomerativeClustering
from scipy.cluster.hierarchy import dendrogram

import numpy as np
from sqlite3 import IntegrityError, OperationalError

import matplotlib.pylab as plt
import time


# In[2]:


ARTICLEDB='article.db'
WORDDB='words.db'
VECDB_VERSION=4


# In[3]:


def get_stored_articles(num_articles='-1', debug_print=False, max_len=5000):
    vecs = []
    bag = FONTBagOfWord()
    bag.from_file(WORDDB)
    it = 1
    with ArticleDB(ARTICLEDB) as articleDB:
        if num_articles==-1:
            adb = articleDB.get()
        else:
            adb = articleDB.get_random(num_articles)

    with ArticleVectorDB() as avdb:
        try:
            avdb.create(ARTICLEDB)
        except OperationalError:
            avdb.conn(ARTICLEDB)
        for article in adb:
            vec = avdb.get(a_id=article['id'],version=VECDB_VERSION)
            if vec:
                vecs.append({'vector':vec,'article':article})
            else:
                proc = {'data':bag.process(article['contents'])}
                vecs.append({'vector':proc, 'article':article})
                avdb.update(a_id=article['id'], version=VECDB_VERSION, index=proc['data'][0], freq=proc['data'][1])
            if debug_print and it % 100 == 0:
                print("Processed", it, "articles")
            it += 1
    bag.to_file(WORDDB)
    return vecs, bag


# In[4]:


#bag = FONTBagOfWord()
#bag.from_file("words.db")
#articles = get_stored_articles(5000)


# In[5]:


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


# In[6]:


def run_kmeans(article_db, bag, n_clusters, debug_print=False):
    #vecs: list of ((indexvec, freqvec),(id, title, date, contents, category, url))
    #len(vecs): num of articles
    #len(bag): num of words in the bag
    v = np.zeros([len(article_db),len(bag)])
    #v: dataset for clustering algorithm v[i,j]: i-th article, num of words bag[j] used
    try:
        for i in range(len(article_db)):
            for j in range(len(article_db[i]['vector']['data'][0])):
                v[i, article_db[i]['vector']['data'][0][j]] = article_db[i]['vector']['data'][1][j]
    except Exception as e:
        raise(e)
    for i in range(len(v)):
        norm = np.linalg.norm(v[i])
        if norm < 0.00001:
            v[i] = np.zeros(len(v[i]))
            v[i][0] = 1
        else:
            v[i] = v[i] / norm
    if(len(article_db) <= 1000):
        batch_size = len(article_db)
    elif(n_clusters * 1.1 <= 1000):
        batch_size = 1000
    else:
        batch_size = int(n_clusters * 1.1)
    verbose = 0
    if debug_print:
        verbose=1
    kmeans = MiniBatchKMeans(n_clusters=n_clusters, init='random',tol=0.005,
                             batch_size=batch_size, verbose=verbose, reassignment_ratio=10**-3)
    del verbose
    if(len(article_db) < n_clusters):
        raise ValueError("n_samples=" + str(len(article_db)) + " should be >= n_clusters=" + str(n_clusters))
    for i in range(0, len(article_db), batch_size):
        kmeans.fit(v)
    return kmeans


# In[7]:


def run_agglomerative(kmeans_centers):
    clustering = AgglomerativeClustering(n_clusters=None, affinity="euclid",linkage="single",distance_threshold=0).fit(kmeans_centers)
    return clustering


# In[8]:


def plot_dendrogram(model, **kwargs):
    plt.title('Hierarchical Clustering Dendrogram')
    # Create linkage matrix and then plot the dendrogram

    # create the counts of samples under each node
    counts = np.zeros(model.children_.shape[0])
    n_samples = len(model.labels_)
    for i, merge in enumerate(model.children_):
        current_count = 0
        for child_idx in merge:
            if child_idx < n_samples:
                current_count += 1  # leaf node
            else:
                current_count += counts[child_idx - n_samples]
        counts[i] = current_count
    distance = model.distances_
    linkage_matrix = np.column_stack([model.children_, distance,
                                      counts]).astype(float)
    #linkage_matrix = np.column_stack([model.children_, distance, counts]).astype(float)
    # Plot the corresponding dendrogram
    dendrogram(linkage_matrix, **kwargs)
    plt.xlabel("Number of points in node (or index of point if no parenthesis).")
    plt.show()


# In[9]:


def run_clustering(article_num, cnt_kmeans_centers, debug_print=False):
    if debug_print:
        ct = time.time()
        print("Running...")

    articles, bag = get_stored_articles(article_num, debug_print)

    if debug_print:
        print("Retrieved the stored articles.")
        print(time.time() - ct, "seconds elapsed")
        ct = time.time()
        print("Running kmeans algorithm...")

    kmeans = run_kmeans(articles, bag, cnt_kmeans_centers, debug_print)

    if debug_print:
        print("Running Agglomerative algorithm...")

    tree = run_agglomerative(kmeans.cluster_centers_)
    print(time.time() - ct, "seconds elapsed")

    if debug_print:
        print("Plotting...")
        plot_dendrogram(tree)
        print("Done")
        print(time.time() - ct, "seconds elapsed")

    return articles, kmeans, tree


# In[16]:


if __name__ == '__main__':
    import winsound
    run_crawler(20,debug_print=True)
    
    #try:
    #    articles, kmeans, tree = run_clustering(1500,100, debug_print=True)
    #except Exception as e:
    #    winsound.Beep(500,500)
    #    raise(e)
    winsound.Beep(1000,500)


# In[11]:


def _iter_tree_downward(tree, cluster_id):
    if cluster_id - len(tree.labels_) < 0:
        yield cluster_id
    else:
        cluster_id -= len(tree.labels_)
        for i in _iter_tree_downward(tree, tree.children_[cluster_id][0]):
            yield i
        for i in _iter_tree_downward(tree, tree.children_[cluster_id][1]):
            yield i

def _iter_tree_from(tree, cluster_id):
    yield cluster_id
    current = cluster_id
    for i in range(len(tree.children_)):
        if(tree.children_[i][0] == current):
            for j in _iter_tree_downward(tree, tree.children_[i][1]):
                yield j
            current = i + len(tree.labels_)
        elif(tree.children_[i][1] == current):
            for j in _iter_tree_downward(tree, tree.children_[i][0]):
                yield j
            current = i + len(tree.labels_)


# In[12]:


def print_all_in_kmeans(kmeans, articles, category):
    print([articles[i] for i in range(len(kmeans.labels_)) if kmeans.labels_[i]==category])

def print_articles_in_kmeans(kmeans, articles, category):
    result = [articles[i]['article']['contents'] for i in range(len(kmeans.labels_)) if kmeans.labels_[i]==category] 
    print(str(category)+'('+str(len(result))+')', end=' ')
#    print('\n\n'.join(result))

def print_categories_by_topics(kmeans, articles, topic):
    result = [kmeans.labels_[i] for i in range(len(articles)) if articles[i]['article']['category'] == '정치']
    print([kmeans.labels_[i] for i in range(len(result))])
    return result

def print_vector_in_kmeans(kmeans, articles):
    print([articles[i]['vector']['data'] for i in range(len(kmeans.labels_)) if kmeans.labels_[i]==category])


# In[13]:


def predict(kmeans, tree, contents):
    bag = FONTBagOfWord()
    bag.from_file(WORDDB)
    idx, freq = bag.process(contents)
    vector = np.zeros(len(bag))
    for i in range(len(idx)):
        vector[idx[i]] = freq[i]
    vector /= np.linalg.norm(vector)
    klabel = kmeans.predict([vector])
    tlabel = tree.labels_[klabel][0]
    print(klabel[0])
   #t_to_k = [0]*len(tree.labels_)
   # for i in range(len(tree.labels_)):
   #     t_to_k[tree.labels_[i]] = i
   # for i in _iter_tree_from(tree, tlabel):
   #     print_articles_in_kmeans(kmeans, articles, t_to_k[i])
   #     print('\n\n\n\n\n--------------------------\n\n\n\n\n')


# In[ ]:




