class MetaUtil():
    def __init__(self) -> None:
        return
    def newMeta(self):
        meta = dict()
        return meta

M = MetaUtil()
PENDING = 0
DOWNLOADING = 1
DONE = 2

class Gallery():
    def __init__(self,url) -> None:
        self.url = url
        self.meta = M.newMeta()
    def checkLocal(self):
        pass
    def parse(self):
        pass
    def downloadPipe(self):
        pass
    def report(self):
        pass

class Img():
    def __init__(self) -> None:
        pass
    def download(self):
        pass