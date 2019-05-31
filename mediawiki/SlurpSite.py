import http.client
import urllib.parse
from html.parser import HTMLParser

class SlurpLinkParser(HTMLParser):
  def handle_starttag(self, tag, attrs):
    if tag == 'a' or tag == 'img':
      attr = dict(attrs)
      self.links.append(attr)

class SlurpSite:
  def __init__(self,params):
    self.params = params
    self.loglevel = 0
    self.maxcount = params['count'] if 'count' in params else None
    self.pending = []
    self.processed = set()
    self.data = {}

  def log(self,text,level = 1):
    if self.loglevel >= level:
      print(text)

  def setlog(self,level = None):
    if level != None:
      self.loglevel = level
    return self.loglevel

  def addToPending(self,path):
    pathparts = urllib.parse.urlparse(path)

    if pathparts.netloc and pathparts.netloc != self.params['host']:
      self.log(".. URL "+path+" pointing to a third-party web site, ignored",2)
    else:
      if pathparts.query:
        self.log(".. IGNORING QUERY IN "+path)
      if not pathparts.path in self.processed:
        if not pathparts.path in self.pending:
          self.pending.append(pathparts.path)
          self.log(".. adding "+pathparts.path+" to pending",2)
      else:
        self.log(".. "+pathparts.path+" already processed, skipped",3)

  def readWebPage(self,url):
    host = self.params['host']
    addr = self.params['addr'] if 'addr' in self.params else host
    conn = http.client.HTTPSConnection(addr)
    conn.request("GET",url,headers = { "Host" : host })
    r = conn.getresponse()
    return r

  def processRedirect(self,url,nexturl):
    self.data[url] = { 'redirect': nexturl }
    return

  def processHTMLData(self,data):
    parser = SlurpLinkParser()
    parser.links = []
    parser.feed(data)
    for link in parser.links:
      if 'href' in link:
        self.addToPending(link['href'])
      if 'src' in link:
        self.addToPending(link['src'])

  def processPage(self,url):
    self.log("Reading "+url)
    r = self.readWebPage(url)
    self.processed.add(url)
    if r.status > 300 and r.status < 400:
      redirect = r.getheader("Location")
      self.log(".. redirect: "+redirect)
      self.processRedirect(url,redirect)
      self.addToPending(redirect)
    else:
      data = r.read()
      content = r.getheader("Content-Type")
      self.log(".. got data: %d bytes" % len(data),2)
      self.data[url] = { 'content': content, 'data': data }
      if "text/html" in content:
        self.processHTMLData(data.decode('utf-8'))

  def Slurp(self,root):
    self.pending.append(root)
    while len(self.pending) > 0:
      self.processPage(self.pending.pop())
      if self.maxcount != None:
        self.maxcount = self.maxcount - 1
        if self.maxcount <= 0:
          return self.data
    return self.data
