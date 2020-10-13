#!/usr/bin/env python
# coding: utf-8

# In[1]:


from Algorithm.tags import FONTBagOfWord, WordDB
from crawler.naver_crawler import crawl_naver_newest as crawl
from crawler.naver_crawler import crawl_naver_one as crawl_one
from crawler.naver_crawler import Article, InternalServerError
from crawler.database import ArticleDB
from sklearn.cluster import KMeans, MiniBatchKMeans, AgglomerativeClustering
from scipy.cluster.hierarchy import dendrogram
import numpy as np
import requests as req
from bs4 import BeautifulSoup
from sqlite3 import IntegrityError
import matplotlib as mpl
import matplotlib.pylab as plt


# In[2]:


def get_stored_articles(num_articles='-1'):
    articleDB = ArticleDB()
    vecs = []
    bag = FONTBagOfWord()
    i = 0
    articleDB.conn('article.db')
    for article in articleDB.get_random(num_articles):
        vecs.append((bag.process(article[3]),article))
        i += 1
        if i % 100 == 0:
            print("processed " + str(i) + " articles")
        if(i == num_articles):
            break
    articleDB.close()
    return vecs


# In[3]:


bag = FONTBagOfWord()
bag.from_file("words.db")
articles = get_stored_articles(5000)


# In[4]:


def run_crawler(num_of_page):
    articleDB = ArticleDB()
    generator = crawl(num_of_page, return_urls_only=True)
    count = 0
    try:
        articleDB.create('article.db')
    except:
        articleDB.conn('article.db')
    while True:
        try:
            article = next(generator)
        except StopIteration:
            break
        except InternalServerError:
            continue
        except Exception as e:
            raise(e)
        if(article):
            try:
                exists = articleDB.get(url=article)
                if exists:
                    article = crawl_one(article)
                    vec = (bag.process(article[2]),article)
                    #((indexvec, freqvec),[title, date, contents, category, url])
            except InternalServerError as e:
                pass
            except Exception as e:
                raise(e)
            if(vec and vec[0] and vec[0][0] and vec[0][1]):
                bag.to_file("words.db")
                try:
                    articleDB.update(article)
                except IntegrityError:
                    continue
                else:
                    count = count + 1
                    if(count % 10 == 0):
                        print("got " + str(count) + " articles")
    articleDB.close()


# In[131]:


def run_kmeans(article_db, n_clusters):
    #vecs: list of ((indexvec, freqvec),(id, title, date, contents, category, url))
    #len(vecs): num of articles
    #len(bag): num of words in the bag
    v = np.zeros([len(article_db),len(bag)])
    #v: dataset for clustering algorithm v[i,j]: i-th article, num of words bag[j] used
    for i in range(len(article_db)):
        for j in range(len(article_db[i][0])):
            v[i, article_db[i][0][0][j]] = article_db[i][0][1][j]
    for i in range(len(v)):
        v[i] = v[i] * (10000 / np.linalg.norm(v[i]))
    batch_size = int(n_clusters * 1.1)
    kmeans = MiniBatchKMeans(n_clusters=n_clusters, init='random',max_no_improvement=None,
                             max_iter=30,batch_size=batch_size, verbose=1, reassignment_ratio=0)
    if(len(article_db) < n_clusters):
        raise ValueError("n_samples=" + str(len(article_db)) + " should be >= n_clusters=" + str(n_clusters))
    for i in range(0, len(article_db), batch_size):
        #kmeans.partial_fit(v[i:i + batch_size, :])
        kmeans.fit(v)
    
    print(kmeans)
    print(kmeans.labels_)
    print(kmeans.cluster_centers_)
    print(kmeans.inertia_)
    return kmeans


# In[122]:


def run_agglomerative(kmeans_centers):
    clustering = AgglomerativeClustering(n_clusters=None, affinity="euclidean",linkage="ward",distance_threshold=80).fit(kmeans_centers)
    return clustering


# In[123]:


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

    linkage_matrix = np.column_stack([model.children_, model.distances_,
                                      counts]).astype(float)

    # Plot the corresponding dendrogram
    dendrogram(linkage_matrix, **kwargs)
    plt.xlabel("Number of points in node (or index of point if no parenthesis).")
    plt.show()


# In[124]:


def run_clustering(cnt_kmeans_centers):
    print("Running...")
    articles = get_stored_articles()
    print("Retrieved the stored articles.")
    print("Running kmeans algorithm...")
    kmeans = run_kmeans(articles, cnt_kmeans_centers)
    print("Running Agglomerative algorithm...")
    tree = run_agglomerative(kmeans.cluster_centers_)
    print("Plotting...")
    plot_dendrogram(tree)
    print("Done")


# In[125]:


if __name__ == '__main__':
#    run_crawler(50000)
#    run_clustering(cnt_kmeans_centers=2500)
    pass


# In[126]:


with ArticleDB('article.db') as db:
    data = db.get()


# In[127]:


len(data)


# In[128]:


del data


# In[129]:


def run_spherical_kmeans(article_db, n_clusters):
    #vecs: list of ((indexvec, freqvec),(id, title, date, contents, category, url))
    #len(vecs): num of articles
    #len(bag): num of words in the bag
    v = np.zeros([len(article_db),len(bag)])
    #v: dataset for clustering algorithm v[i,j]: i-th article, num of words bag[j] used
    for i in range(len(article_db)):
        for j in range(len(article_db[i][0])):
            v[i, article_db[i][0][0][j]] = article_db[i][0][1][j]
    for i in range(len(v)):
        v[i] = v[i] / np.linalg.norm(v[i])
    del article_db
    print("running KMeans...")
    kmeans = KMeans(n_clusters=n_clusters, init='random', max_iter=20, verbose=1).fit(v)
    #kmeans = SphericalKMeans(n_clusters=n_clusters, init='similar_cut', max_iter=10).fit(v)
    print("Done...")
    print(kmeans)
#    print(kmeans.labels_)
#    print(kmeans.cluster_centers_)
#    print(kmeans.inertia_)
    return kmeans


# In[145]:


kmeans = run_kmeans(articles,min(int(0.6 * len(articles)), 5000))
for i in sorted(kmeans.labels_):
    print(i, end=' ')


# In[91]:


def print_all_in_kmeans(kmeans, articles, category):
    print([articles[i] for i in range(len(kmeans.labels_)) if kmeans.labels_[i]==category])

def print_articles_in_kmeans(kmeans, articles, category):
    print('\n\n'.join([articles[i][1][3] for i in range(len(kmeans.labels_)) if kmeans.labels_[i]==category]))

def print_vector_in_kmeans(kmeans, articles):
    print([(articles[i][0][0], articles[i][0][1]) for i in range(len(kmeans.labels_)) if kmeans.labels_[i]==category])


# In[155]:


print_articles_in_kmeans(kmeans,articles,84)
#print_articles_in_kmeans(kmeans,articles,0)


# In[16]:


import winsound
winsound.Beep(500,1000)


# In[146]:


def get_cluster_dist(kmeansRes, a, b):
    return np.linalg.norm(kmeansRes.cluster_centers_[a] - kmeansRes.cluster_centers_[b]) / 10000


# In[109]:


import itertools
a = 0
for i, j in itertools.combinations(range(len(kmeans.cluster_centers_)), 2):
    if get_dist(kmeans,i,j) < 0.1:
        a += 1
print(a)


# In[100]:


get_dist(kmeans, 665, 679)


# In[ ]:




