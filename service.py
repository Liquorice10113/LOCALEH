from math import ceil
import os
from flask import Flask, jsonify, render_template, send_from_directory, request, Response
from threading import Thread,Lock
from eh_handler import *

class GalleryManager(Thread):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
    def run(self):
        global galleries_url_in, galleries, SIG_UPDATE_GALLERY_INFO
        while True:
            while len(galleries_url_in) >0:
                galleries_url_in_Lock.acquire()
                url_in = galleries_url_in.pop(0)
                galleries_url_in_Lock.release()
                gid = re.search('e-hentai.org\/g\/(\w+\/\w+\/)',url_in).group(1)
                #gid = gid.replace('/','')
                g = Gallery(url_in)
                g.meta['title'] = 'Parsing...'
                g.parse()
                g.checkLocal()
                new_gid = re.search('e-hentai.org\/g\/(\w+\/\w+\/)',g.url).group(1)
                if gid in galleries:
                    del galleries[gid]
                if new_gid in galleries:
                    del galleries[new_gid]
                for ogid in galleries:
                    if galleries[ogid].meta['title'] == g.meta['title']:
                        del galleries[ogid]
                gid = new_gid
                galleries[gid] = g
            for gid in galleries:
                g = galleries[gid]
                if g.meta['status'] == DONE or g.meta['status'] == LEGACY:
                    continue
                jobFinishedFlag = True
                for img in g.images:
                    if img.status == PENDING:
                        if not img in imgQ:
                            imgQ.append(img)
                        jobFinishedFlag = False
                    elif img.status == DOWNLOADING:
                        jobFinishedFlag = False
                    elif img.status == ERROR:
                        jobFinishedFlag = False
                if jobFinishedFlag:
                    g.meta['status'] = DONE
            if SIG_UPDATE_GALLERY_INFO:
                SIG_UPDATE_GALLERY_INFO = False
                update_gallery_info()
            if SIG_STOP_MANAGER:
                break
            time.sleep(1)


class DownloadManager(Thread):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args,**kwargs)
    def run(self):
        while True:
            imgQLock.acquire()
            if len(imgQ)>0:
                img = imgQ.pop(0)
                imgQLock.release()
                img.download()
            else:
                imgQLock.release()
                time.sleep(1)
            if SIG_STOP_MANAGER:
                break

def update_gallery_info():
    global gallery_info
    gallery_info = []
    for gid in galleries:
        g = galleries[gid]
        g.checkLocal()
        gallery_info.append(
            {
                'gid':gid,
                "title":g.meta['title'],
                'length':g.meta['lenght'],
                'status':g.meta['status'],
                'thumb':g.images[0]
            }
         )

def loadFromLocal():
    for folder in os.listdir(BASE):
        if not os.path.isdir( os.path.join(BASE,folder) ):
            continue
        if os.path.isfile( os.path.join(BASE,folder,'gallery.json') ):
            g = Gallery()
            g.loadFromLocal(os.path.join(BASE,folder,'gallery.json'))
            gid = re.search('e-hentai.org\/g\/(\w+\/\w+\/)',g.meta['url']).group(1)
            galleries[gid] = g
        elif os.path.isfile( os.path.join(BASE,folder,'meta.json') ):
            g = Gallery()
            g.loadFromLegacy(os.path.join(BASE,folder,'meta.json'),os.path.join(BASE,folder),folder)
            gid = re.search('e-hentai.org\/g\/(\w+\/\w+\/)',g.meta['url']).group(1)
            galleries[gid] = g
        

SIG_STOP_MANAGER = False
SIG_UPDATE_GALLERY_INFO = False
gallery_info = None

galleries_url_in = []
#galleries_url_in = ['https://e-hentai.org/g/2174441/e056e87231/']
galleries_url_in_Lock = Lock()

imgQ = []
imgQLock = Lock()

galleries = dict()
galleriesLock = Lock()

loadFromLocal()

w = GalleryManager()
w.setDaemon(True)
w.start()

dm = DownloadManager()
dm.setDaemon(True)
dm.start()

app = Flask(__name__)

@app.route("/")
def gallery_index():
    global galleries
    galleries_jinja_data = []
    for gid in galleries:
        g = galleries[gid]
        galleries_jinja_data.append({
            "gid":gid,
            "title":g.meta['title'],
            "thumb":g.meta['title']+'/'+g.images[0].name,
            'status':g.meta['status']
        })
    return render_template("index.html",galleries=galleries_jinja_data)

@app.route("/g/<path:gid>")
def gallery(gid):
    #gid = gid.replace('/','')
    IMG_PER_PAGE = 12
    p = 0
    if 'p' in request.args:
        p = int(request.args['p'])
    if not gid[-1] == '/':
        gid = gid +'/'
    images = []
    if gid in galleries:
        for img in galleries[gid].images[p*IMG_PER_PAGE:(p+1)*IMG_PER_PAGE]:
            images.append({
                "title":img.name,
                "status":img.status,
                "thumb":img.parentMeta['title']+'/'+img.name
            })
        return render_template("images.html",images=images, cnt= ceil(len(galleries[gid].images)/IMG_PER_PAGE),gid=gid, title=galleries[gid].meta['title'],p=p )
    return Response("Not found!",404)

@app.route("/s/<title>/<fn>")
def image(title,fn):
    if os.path.exists(os.path.join(BASE,title,fn)):
        return send_from_directory( os.path.join(BASE,title),fn )
    else:
        return Response("Not found!",404)

@app.route('/add', methods=['POST'])
def url_in():
    url = request.form['url_in']
    if not re.match('https\:\/\/e\-hentai\.org\/g\/\w+\/\w+\/',url):
        return "<script>alert('Nope')</script>"
    galleries_url_in_Lock.acquire()
    galleries_url_in.append(url)
    galleries_url_in_Lock.release()
    print(url)
    return "<script>alert('OK')</script>"

app.run('0.0.0.0',8080,debug=True)

