#!/usr/bin/env python
# coding: utf-8

# In[1]:


from Algorithm.tags import FONTBagOfWord, WordDB

from crawler.database import ArticleDB, ArticleVectorDB
from sklearn.cluster import MiniBatchKMeans, AgglomerativeClustering
from scipy.cluster.hierarchy import dendrogram
import numpy as np
from sqlite3 import IntegrityError, OperationalError

import matplotlib.pylab as plt
import time

import jpype
from threading import Thread, Lock


# In[2]:


ARTICLEDB='database.db'
WORDDB='words.db'
VECDB_VERSION=1


# In[3]:


def multi_t_process_article(bag, article, result_pool, lock):
    jpype.attachThreadToJVM()
    result_pool.append(
        (article,
         bag.process(article['contents'], lock=lock)
        )
    )
    return

def multi_t_count(wordcnt, vec, lock):
    idx = vec[1][0]
    freq = vec[1][1]
    length = len(vec[1][0])
    for i in range(length):
        lock.acquire()
        try:
            wordcnt[idx[i]] += freq[i]
        except IndexError:
            wordcnt += [0] * (idx[i] - len(wordcnt) + 1)
            wordcnt[idx[i]] = freq[i]
        lock.release()
    return


def get_stored_articles(num_articles='-1', max_len=5000, num_threads=32, debug_print=False):
    vecs = []
    bag = FONTBagOfWord()
    bag.from_file(WORDDB)
    it = 0
    wordcnt = [0] * len(bag)
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
            
        for articles in np.array_split(adb, len(adb) // num_threads):
            threads = []
            results = []
            lock = Lock()
            for article in articles:
                vec = avdb.get(a_id=article['id'], version=VECDB_VERSION)
                if vec:
                    vec = vec['data']
                    if(len(vec) != 2):
                        print(vec)
                    results.append((article, vec))
                else:
                    threads.append(Thread(target=multi_t_process_article, args=(bag, article, results, lock)))

            for t in threads:
                t.start()
            for t in threads:
                t.join()
            for vec in results:
                avdb.update(a_id=article['id'], version=VECDB_VERSION, index=vec[1][0], freq=vec[1][1])
            threads = []
            for vec in results:
                vecs.append({'article':vec[0], 'vector':vec[1]})
                threads.append(Thread(target=multi_t_count, args=(wordcnt, vec, lock)))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if debug_print:
                it += num_threads
                print("Processed", it, "articles")

    rank = np.argsort(np.argsort(wordcnt)[::-1])
    most_freq = np.argsort(wordcnt)[::-1]
    for i in range(50):
        print(bag.get(most_freq[i]))
    for i in range(len(vecs)):
        vec = np.zeros(max_len)
        idx = [rank[j] for j in vecs[i]['vector'][0]]
        freq = vecs[i]['vector'][1]
        for j in range(len(idx)):
            if(idx[j] < max_len):
                vec[idx[j]] = freq[j]
        vecs[i]['vector'] = vec
        if (i+1) % 100 == 0:
            print("Vectorized", i+1, "articles")
    bag.to_file(WORDDB)
    return vecs, bag


# In[4]:


def run_kmeans(article_db, bag, n_clusters,  max_len=5000, debug_print=False):
    
    v = np.zeros([len(article_db),max_len])
    #v: dataset for clustering algorithm v[i,j]: i-th article, num of words bag[j] used
    for i in range(len(article_db)):
        v[i] = article_db[i]['vector']

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
    kmeans = MiniBatchKMeans(n_clusters=n_clusters, init='k-means++',max_iter=150,
                             batch_size=batch_size, verbose=verbose, reassignment_ratio=0.02)
    del verbose
    if(len(article_db) < n_clusters):
        raise ValueError("n_samples=" + str(len(article_db)) + " should be >= n_clusters=" + str(n_clusters))
    kmeans.fit(v)
    return kmeans


# In[5]:


def run_agglomerative(kmeans_centers):
    clustering = AgglomerativeClustering(n_clusters=None, affinity="cosine",linkage="single",distance_threshold=0).fit(kmeans_centers)
    return clustering


# In[6]:


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


# In[7]:


def run_clustering(n_articles, n_clusters, max_len=5000, num_threads=32, debug_print=False):
    if debug_print:
        ct = time.time()
        print("Running...")
    articles, bag = get_stored_articles(n_articles, max_len=max_len, num_threads=num_threads, debug_print=debug_print)

    if debug_print:
        print("Retrieved the stored articles.")
        print(time.time() - ct, "seconds elapsed")
        ct = time.time()
        print("Running kmeans algorithm...")

    kmeans = run_kmeans(articles, bag, n_clusters, max_len, debug_print)

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


# In[8]:


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


# In[9]:


def all_in_kmeans(kmeans, articles, category):
    return [articles[i] for i in range(len(kmeans.labels_)) if kmeans.labels_[i]==category]

def articles_in_kmeans(kmeans, articles, category):
    result = [articles[i]['article']['contents'] for i in range(len(kmeans.labels_)) if kmeans.labels_[i]==category] 
    return result

def categories_by_topics(kmeans, articles, topic):
    result = [kmeans.labels_[i] for i in range(len(articles)) if articles[i]['article']['category'] == '정치']
    return result

def vector_in_kmeans(kmeans, articles):
    print([articles[i]['vector']['data'] for i in range(len(kmeans.labels_)) if kmeans.labels_[i]==category])


# In[10]:


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


# In[11]:


def evaluate(kmeans, articles):
    n_category = ['사회','정치','IT','경제','생활','오피니언','세계']
    article_category = {}
    for i in n_category:
        article_category[i] = []
    for i, article in enumerate(articles):
        category = article['article']['category']
        if category != '':
            article_category[category].append(i)
    #print(article_category)
    for key, i in article_category.items():
        sum = 0
        for j in i:
            for k in i:
                sum += np.linalg.norm(
                    kmeans.cluster_centers_[kmeans.labels_[j]] - 
                    kmeans.cluster_centers_[kmeans.labels_[k]]
                )
        sum /= (len(i) * len(i))
        print('category: ' + key + ',cost= ' + str(sum))
    sum = 0
    #for i in range(len(articles)):
    #    for j in range(len(articles)):
    #        sum += np.linalg.norm(
    #            kmeans.cluster_centers_[kmeans.labels_[i]] - 
    #            kmeans.cluster_centers_[kmeans.labels_[j]]
    #        )
    #sum /= (len(articles) * len(articles))
    #print('total: cost= ' + str(sum))
    #sum = 0
    #n = 0
    #for i, item in enumerate(articles):
    #    for j, jtem in enumerate(articles):
    #        if(item['article']['category'] != jtem['article']['category']):
    #            sum += np.linalg.norm(
    #                kmeans.cluster_centers_[kmeans.labels_[i]] - 
    #                kmeans.cluster_centers_[kmeans.labels_[j]]
    #            )
    #            n += 1
    #if(len(articles) > 1):
    #    sum /= n
    #print("cost(different category):", sum)


# In[12]:


if __name__ == '__main__':
    #param: max_len, n_clusters,num_threads, max_len, debug_print
    import winsound
    try:
        n_clusters = 200
        articles, kmeans, tree = run_clustering(500,n_clusters, num_threads=64,max_len=8000, debug_print=True)
    except Exception as e:
        winsound.Beep(500,500)
        raise(e)
    winsound.Beep(1000,500)
    evaluate(kmeans, articles)
    for i in range(n_clusters):
        print('category=', i)
        for article in all_in_kmeans(kmeans, articles, i):
            print(article['article']['title'],'((',article['article']['category'],'))', end='\n\n')
        print('=============================================')
        input()


# In[ ]:




