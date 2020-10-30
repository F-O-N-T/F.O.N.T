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


# In[2]:


ARTICLEDB='article.db'
WORDDB='words.db'
VECDB_VERSION=7


# In[3]:


def get_stored_articles(num_articles='-1', debug_print=False, max_len=5000):
    vecs = []
    bag = FONTBagOfWord()
    bag.from_file(WORDDB)
    it = 1
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
        for article in adb:
            vec = avdb.get(a_id=article['id'],version=VECDB_VERSION)
            if vec:
                vec = vec['data']
                if(len(vec) != 2):
                    print(vec)
                vecs.append({'vector':vec,'article':article})
            else:
                vec = bag.process(article['contents'])
                vecs.append({'vector':vec, 'article':article})
                avdb.update(a_id=article['id'], version=VECDB_VERSION, index=vec[0], freq=vec[1])
            idx = vec[0]
            freq = vec[1]
            length = len(vec[0])
            for i in range(length):
                try:
                    wordcnt[idx[i]] += freq[i]
                except IndexError:
                    wordcnt += [0] * (idx[i] - len(wordcnt) + 1)
                    wordcnt[idx[i]] = freq[i]
            if debug_print and it % 100 == 0:
                print("Processed", it, "articles")
            it += 1

    rank = np.argsort(np.argsort(wordcnt)[::-1])
    for i in range(len(vecs)):
        vec = np.zeros(max_len)
        idx = vecs[i]['vector'][0]
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


def run_kmeans(article_db, bag, n_clusters, debug_print=False, max_len=5000):
    
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
    kmeans = MiniBatchKMeans(n_clusters=n_clusters, init='random',tol=0.005,
                             batch_size=batch_size, verbose=verbose, reassignment_ratio=10**-3)
    del verbose
    if(len(article_db) < n_clusters):
        raise ValueError("n_samples=" + str(len(article_db)) + " should be >= n_clusters=" + str(n_clusters))
    for i in range(0, len(article_db), batch_size):
        kmeans.fit(v)
    return kmeans


# In[5]:


def run_agglomerative(kmeans_centers):
    clustering = AgglomerativeClustering(n_clusters=None, affinity="euclid",linkage="single",distance_threshold=0).fit(kmeans_centers)
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


def run_clustering(n_articles, n_clusters, debug_print=False):
    if debug_print:
        ct = time.time()
        print("Running...")

    articles, bag = get_stored_articles(n_articles, debug_print)

    if debug_print:
        print("Retrieved the stored articles.")
        print(time.time() - ct, "seconds elapsed")
        ct = time.time()
        print("Running kmeans algorithm...")

    kmeans = run_kmeans(articles, bag, n_clusters, debug_print)

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


if __name__ == '__main__':
    import winsound
    try:
        articles, kmeans, tree = run_clustering(500,50, debug_print=True)
    except Exception as e:
        winsound.Beep(500,500)
        raise(e)
    winsound.Beep(1000,500)
    for i in range(50):
        print('category=', i)
        for article in articles_in_kmeans(kmeans, articles, i):
            print(article, end='\n\n')
        print('=============================================')
        input()

