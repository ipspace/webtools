import http.client
import urllib.parse
import os
import re
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
    urlparts = urllib.parse.urlparse(nexturl)
    if urlparts.netloc and (urlparts.netloc == self.params['host'] or urlparts.netloc in self.get('alias')):
      nexturl = urlparts.path
      if urlparts.query:
        nexturl = nexturl + "?" + urlparts.query

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

  def removeHTMLComments(self,data):
    return re.sub("(<!--.*?-->)", "", data, flags=re.DOTALL)

  def saveWebPage(self,url,data,conType):
    output = self.params.get('output',None)
    if output == None:
      sys.exit("FATAL: Cannot save data, OUTPUT parameter not specified")
    if url.find('/') != 0:
      sys.exit("FATAL: URL "+url+" does not start with a /")

    path = os.path.dirname(url)
    name = os.path.basename(url)

    # Dirty hack - for MW-style pages we have to emulate a directory
    # if the path contains a '.'
    if '.' in path and not '.' in name:
      path = url
      url  = url + '/index.html'

    # Move paths to within the target directory
    path = output + path
    fname = output + url

    binary = 'b'
    if 'text' in conType:
      binary = ''
      data = data.decode('utf-8')

    if 'html' in conType and self.params.get('comments') == 'remove':
      data = self.removeHTMLComments(data)

# Try to make a directory path. It will fail with FileExistsError in which
# case we have to move the existing file into directory/index.html
#

    self.log("... saving data in "+path,2)
    try:
      os.makedirs(path,exist_ok=True)
    except FileExistsError:
      self.log("... OOPS, making "+path+" into a directory",3)
      os.rename(path,path+'.tmp')
      os.makedirs(path)
      os.rename(path+'.tmp',path+'/index.html')

# Try to create the output file. If a directory with the same name exists,
# create index.html in that directory
#
    try:
      outfile = open(fname,'w'+binary)
    except IsADirectoryError:
      self.log("... OOPS, making "+fname+" is a directory",3)
      outfile = open(fname+'/index.html','w'+binary)

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
