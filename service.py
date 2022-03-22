import os
from flask import Flask, jsonify, send_from_directory
from threading import Thread
from eh_handler import *

class Worker(Thread):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
    def run(self):
        global galleries_url_in, galleries
        while True:
            if len(galleries_url_in) >0:
                url_in = galleries_url_in.pop(0)
                gid = re.search('e-hentai.org\/g\/(\w+\/\w+\/)',url_in).group(1)
                #gid = gid.replace('/','')
                if gid in galleries:
                    galleries[gid].meta['status'] = PENDING
                    downQ.append(gid)
                else:
                    g = Gallery(url_in)
                    g.meta['title'] = 'Parsing...'
                    galleries[gid] = g
                g.parse()
            time.sleep(1)

def loadFromLocal():
    for folder in os.listdir(BASE):
        if not os.path.isdir( os.path.join(BASE,folder) ):
            continue
        if not os.path.isfile( os.path.join(BASE,folder,'gallery.json') ):
            continue
        g = Gallery()
        g.loadFromLocal(os.path.join(BASE,folder,'gallery.json'))
        gid = re.search('e-hentai.org\/g\/(\w+\/\w+\/)',g.meta['url']).group(1)
        galleries[gid] = g

#galleries_url_in = ['https://e-hentai.org/g/2172783/f13044f2c5/']
galleries_url_in = []
downQ = []
galleries = dict()

loadFromLocal()

w = Worker()
w.start()

app = Flask(__name__)

@app.route("/")
def gallery_index():
    global galleries
    resp = ''
    seg = '<a href="/g/{}">{}</a></br>'
    for gid in galleries:
        g = galleries[gid]
        resp += seg.format(gid,g.meta['title'] )
    return resp

@app.route("/g/<path:gid>")
def gallery(gid):
    #gid = gid.replace('/','')
    if not gid[-1] == '/':
        gid = gid +'/'
    seg = '<a href="/s/{0}/{1}">{1}</a>{2}</br>'
    if gid in galleries:
        resp = galleries[gid].meta['title']+'</br>'
        for img in galleries[gid].images:
            resp += seg.format(galleries[gid].meta['title'],img.name,status[img.status])
        return resp
    return 404

@app.route("/s/<title>/<fn>")
def image(title,fn):
    if os.path.exists(os.path.join(BASE,title,fn)):
        return send_from_directory( os.path.join(BASE,title),fn )
    else:
        return 404

app.run('0.0.0.0',8080,debug=True)

