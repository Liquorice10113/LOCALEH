import time
import requests as req
from bs4 import BeautifulSoup
import re,os
from html import unescape
import json

BASE = './COMIC/'

C = { "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36"}, "proxies": {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}, "cookies": {"__cfduid": "d3a4b57bde61a4b17c12d649f9bb44e521620030396", "event": "1620131041", "hath_perks": "m1.m2.m3.a.t1.t2.p1.s.q-b74fce7784", "ipb_member_id": "4051477", "ipb_pass_hash": "928b26b5503552470761db30ccd71fb7", "sk": "g432vw9uvmwdrxpserwmyokq6na2", "sl": "dm_1","nw":"1"}}


class MetaUtil():
    def __init__(self) -> None:
        return
    def newMeta(self):
        meta = dict()
        meta['title'] = None
        meta['url'] = None
        meta['length'] = None
        meta['modified'] = time.time()
        meta['status'] = PENDING
        meta['tags'] = []
        return meta

M = MetaUtil()

status = [ 'PENDING','DOWNLOADING','DONE','FINISHED','ONGOING' ]

PENDING = 0
DOWNLOADING = 1
DONE = 2

FINISHED = 3
ONGOING = 4

#C = dict()

def wash(s):
    s = unescape(s)
    for i in "\/:*?\"<>|":
        s = s.replace(i, '')
    return s


def uniCnt(cnt):
    return (3-len(str(cnt)))*'0'+str(cnt)

def sw(s,*args):
    return s

def log(s):
    print(time.ctime(),s)

def get(url, binary=False, stream=False):
    # print(url)
    global C
    if "509.gif" in url:
        log("Limits reached maybe?")
    rc = 1
    while True:
        try:
            resp = req.get(url, headers=C['headers'], cookies=C['cookies'], proxies=C['proxies'])
            if binary:
                return resp.content
            else:
                return resp.text
        except KeyboardInterrupt:
            log('KeyboardInterrupt')
            raise
        except Exception as e:
            raise
            print(e)
            if rc > 6:
                #raise Exception("Download Failed.")
                log('Failed after 6 attemps.')
                raise
                return b''
            time.sleep(5)
            log('Retrying')
            rc += 1


class Gallery():
    def __init__(self,url=None) -> None:
        self.url = url
        self.meta = M.newMeta()
        self.meta['url'] = url
        self.images = []
        self.html = ''
    def checkLocal(self):
        pass
    def parse(self):
        try:
            self.html = get(self.url)
            soup = BeautifulSoup(self.html, 'html.parser')
            
            self.meta['title'] = wash(soup.title.text.replace(
                ' - E-Hentai Galleries', ''))
            print(self.meta['title'])
            self.meta['length'] = int(re.search('(\d+) pages', self.html).group(1))

            pageUrls = soup.find(class_="ptt").find_all('a')
            pageUrls = [u.attrs['href'] for u in pageUrls]
            pageUrls = sorted(list(set(pageUrls)))
            for galleryPageUrl in pageUrls:
                self.html = get(galleryPageUrl)
                soup = BeautifulSoup(self.html, 'html.parser')
                for div in soup.find_all('div', class_='gdtm'):
                    index_ = uniCnt(int(div.div.a.img.attrs['alt'])-1)
                    name = re.match('Page \d+: (.+)',
                                    div.div.a.img.attrs['title']).group(1)
                    pageUrl = div.div.a.attrs['href']
                    page = Img(pageUrl,name,self.meta)
                    self.images.append(page)
            if not os.path.exists( os.path.join( BASE,self.meta['title'] ) ):
                os.makedirs(os.path.join( BASE,self.meta['title'] ) )
            self.save2disk()
        except Exception as e:
            raise
            print(e)
            print(sw("Parse failed for:\n"+self.url, c="red"))
            self.errored = True
    def downloadPipe(self):
        pass
    def report(self):
        data = dict()
        data['modified'] = self.meta['modified']
        data['title'] = self.meta['title']
        data['thumb'] = self.images[0].name
        data['length'] = self.meta['length']
        data['status'] = self.meta['status']
        return data
    def detail(self):
        data = dict()
        data['modified'] = self.meta['modified']
        data['title'] = self.meta['title']
        data['thumb'] = self.images[0].name
        data['status'] = self.meta['status']
        data['length'] = self.meta['length']
        data['tags'] = self.meta['tags']
        return data
    def images_detail(self):
        data = []
        for img in self.images:
            data.append({
                'name':img.name,
                'url':img.url,
                'status':img.status
            })
    def save2disk(self):
        data = dict()
        data['meta'] = self.meta
        data['images'] =[p.dump() for p in  self.images]
        meta_fn = os.path.join(BASE,self.meta['title'],'gallery.json')
        json.dump(data,open(meta_fn,'w'))
    def loadFromLocal(self,meta_fn):
        data = json.load(open(meta_fn,'r'))
        self.meta = data['meta']
        self.url = self.meta['url']
        for img in data['images']:
            fn = img['file_name']
            url = img['url']
            img = Img(url,fn,self.meta)
            if os.path.exists( os.path.join(BASE,self.meta['title'],fn) ):
                img.status = DONE
            self.images.append(img)

class Img():
    def __init__(self,url,name,parentMeta,status=PENDING) -> None:
        self.url = url
        self.name = name
        self.parentMeta = parentMeta
        self.status = status
    def download(self):
        pass
    def dump(self):
        data = dict()
        data['file_name'] = self.name
        data['url'] = self.url
        return data