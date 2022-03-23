import time
from unicodedata import name
import requests as req
from bs4 import BeautifulSoup
import re,os
from html import unescape
import json
from threading import Thread,Lock

BASE = './COMIC/'

C = { "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36"}, "proxies": {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}, "cookies": {"__cfduid": "d3a4b57bde61a4b17c12d649f9bb44e521620030396", "event": "1620131041", "hath_perks": "m1.m2.m3.a.t1.t2.p1.s.q-b74fce7784", "ipb_member_id": "4051477", "ipb_pass_hash": "928b26b5503552470761db30ccd71fb7", "sk": "g432vw9uvmwdrxpserwmyokq6na2", "sl": "dm_1","nw":"1"}}


WLock = Lock()

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
        meta['parents'] = []
        return meta

M = MetaUtil()

status = [ 'PENDING','DOWNLOADING','DONE','FINISHED','ONGOING','ERROR','LEGACY' ]

PENDING = 0
DOWNLOADING = 1
DONE = 2
ERROR = 5
ONGOING = 4
LEGACY = 6

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
        self.legacy = False

    def checkLocal(self):
        self.meta['status'] = DONE
        for img in self.images:
            fn = os.path.join(BASE,self.meta['title'],img.name)
            if os.path.exists(fn):
                img.status = DONE
            else:
                img.status = PENDING
                self.meta['status'] = PENDING
    def parse(self):
        if self.legacy:
            return
        try:
            self.html = get(self.url)
            soup = BeautifulSoup(self.html, 'html.parser')
            
            self.meta['title'] = wash(soup.title.text.replace(
                ' - E-Hentai Galleries', ''))
            print(self.meta['title'])

            if "There are newer versions of this gallery available" in self.html:
                print("There are newer versions of this gallery available.")
                print("Hold on...")
                new_url = soup.find(id="gnd").find_all("a")[-1].attrs["href"]
                print("Url changed from:\n"+self.url +
                      "\nto:\n"+new_url)
                self.url = new_url
                self.meta['url'] = new_url
                self.html = get(self.url)
                soup = BeautifulSoup(self.html, 'html.parser')
                new_title = wash(soup.title.text.replace(
                    ' - E-Hentai Galleries', ''))
                if self.meta['title'] != new_title:
                    print("Title changed from:\n"+self.meta['title'] +
                          "\nto:\n"+new_title)
                    try:
                        if os.path.exists(C['folderDir']+self.meta['title']):
                            os.rename(C['folderDir']+self.meta['title'],
                                      C['folderDir']+new_title)
                    except:
                        print("Failed to change folder name! Needs attention.")
                        self.meta['status'] = ERROR
                        return
                    self.meta['title'] = new_title
        
            self.meta['length'] = int(re.search('(\d+) pages', self.html).group(1))

            soup = BeautifulSoup(self.html, 'html.parser')
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
    def loadFromLegacy(self,meta_fn,folder,title):
        data = json.load(open(meta_fn,'r'))
        self.meta = data
        self.legacy = True
        self.meta['status'] = LEGACY
        self.url = self.meta['url']
        self.meta['title'] = title
        for i in os.listdir(folder):
            if i.split('.')[-1].lower() in ['jpg','jpeg','png','bmp','gif']:
                img = Img(None,i,self.meta)
                img.status = LEGACY
                self.images.append(img)

class Img():
    def __init__(self,url,name,parentMeta,status=PENDING) -> None:
        self.url = url
        self.name = name
        self.imgurl = None
        self.parentMeta = parentMeta
        self.status = status
    def download(self):
        global WLock
        if self.status == DONE or self.status == LEGACY:
            return
        self.status = DOWNLOADING
        print("downloading",self.name)
        fn = os.path.join(BASE,self.parentMeta['title'],self.name)
        if os.path.exists(fn):
            self.status = DONE
            return
        try:
            self.html = get(self.url)
            soup = BeautifulSoup(self.html, "html.parser")
            self.imgurl = soup.find(id="img").attrs["src"]
            bin_ = get(self.imgurl,True)
            WLock.acquire()
            with open(fn,'wb') as f:
                f.write(bin_)
            WLock.release()
            self.status = DONE
        except:
            self.status = ERROR
            WLock.release()
            raise

    def dump(self):
        data = dict()
        data['file_name'] = self.name
        data['url'] = self.url
        return data
