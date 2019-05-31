import http.client
import urllib.parse
import os
from html.parser import HTMLParser

class SlurpLinkParser(HTMLParser):
  def __init__(self):
    self.links = []
    super(SlurpLinkParser, self).__init__()

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

  def matchURL(self,url,acl):
    for a in acl:
      for k in a:
        if a[k] in url:
          return k
    return "default"

  def addToPending(self,path,parent):
    pathparts = urllib.parse.urlparse(path)

    if pathparts.netloc and pathparts.netloc != self.params['host']:
      self.log(".. URL "+path+" pointing to a third-party web site, ignored",2)
    else:
      if pathparts.query:
        self.log(".. IGNORING QUERY IN "+path)
      url = pathparts.path
      if url == "":
        return
      if url.find("%") >= 0:
        url = urllib.parse.unquote(url)

# Change relative URLs (those without leading /) into absolute URL
# using parent URL as base
      if url.find('/') != 0:
        pathend = parent.rfind('/')
        url = parent[:pathend+1]+url

      if self.matchURL(url,self.params.get('acl',[])) in ('skip','deny'):
        self.log("... skipping "+url+" due to ACL entry",2)
        return

# Add absolute intra-site URL to pending list if not yet processed
      if not url in self.processed:
        if not url in self.pending:
          self.pending.append(url)
          self.log(".. adding "+url+" to pending",2)
      else:
        self.log(".. "+url+" already processed, skipped",3)

  def readWebPage(self,url):
    host = self.params['host']
    addr = self.params['addr'] if 'addr' in self.params else host
    conn = http.client.HTTPSConnection(addr) if self.params.get('ssl') else http.client.HTTPConnection(addr)
    conn.request("GET",urllib.parse.quote(url),headers = { "Host" : host })
    r = conn.getresponse()
    return r

  def processRedirect(self,url,nexturl):
    self.data[url] = { 'redirect': nexturl }
    return

  def processHTMLData(self,data,url):
    parser = SlurpLinkParser()
    parser.links = []
    parser.feed(data)
    for link in parser.links:
      if 'href' in link:
        self.addToPending(link['href'],url)
      if 'src' in link:
        self.addToPending(link['src'],url)

  def saveWebPage(self,url,data,conType):
    output = self.params.get('output',None)
    if output == None:
      sys.exit("FATAL: Cannot save data, OUTPUT parameter not specified")
    if url.find('/') != 0:
      sys.exit("FATAL: URL "+url+" does not start with a /")

    path = output + os.path.dirname(url)
    binary = 'b'
    if 'text' in conType:
      binary = ''
      data = data.decode('utf-8')
    os.makedirs(path,exist_ok=True)
    with open(output+url,'w'+binary) as outfile:
      outfile.write(data)
      outfile.close()

  def processPage(self,url):
    self.log("Reading "+url)
    r = self.readWebPage(url)
    self.processed.add(url)
    if r.status > 300 and r.status < 400:
      redirect = r.getheader("Location")
      self.log(".. redirect: "+redirect)
      self.processRedirect(url,redirect)
      self.addToPending(redirect,url)
      self.data[url] = { 'redirect': redirect }
    elif r.status > 400:
      self.data[url] = { 'error': r.status }
    else:
      webdata = r.read()
      conType = r.getheader("Content-Type")
      self.log(".. got data: %d bytes" % len(webdata),2)

# Create the object describing the web page
      entry  = { 'content': conType, 'len': len(webdata) }

# Figure out what to do with page data
      action = self.params.get('data')
      if action == "save":
        self.saveWebPage(url,webdata,conType)
      elif action != "drop":
        entry['data'] = webdata

      self.data[url] = entry
      if "text/html" in conType:
        self.processHTMLData(webdata.decode('utf-8'),url)

  def Slurp(self,root):
    self.pending.append(root)
    while len(self.pending) > 0:
      self.processPage(self.pending.pop())
      if self.maxcount != None:
        self.maxcount = self.maxcount - 1
        if self.maxcount <= 0:
          return self.data
    return self.data
