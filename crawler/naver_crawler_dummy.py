import time

class InternalServerError(Exception):
    pass

def crawl_naver_one_slow(url, sec):
    time.sleep(sec)
    return crawl_naver_one(url)

def crawl_naver_one(url):
    title = ""
    date = ""
    contents = ""
    category = ""
    url = ""
    raise NotImplementedError
    dic = {'title':title, 'date':date, 'contents':contents, 'category':category, 'url':url}
    return dic

def crawl_naver_newest(number, return_urls_only=False):
    list_url = []
    if(return_urls_only):
        return list_url
    else:
        for urls in list_url:
            article = crawl_naver_one_slow(article, 0.05)
            if article:
                yield article
            else raise InternalServerError("Failed to Connect the server. Please retry it again.")

if(__name__ == "__main__"):
    c = crawl_naver_newest(50, return_urls_only=True)
    for x in c:
        article = crawl_naver_one(x)
        print(article[0])





