#!/usr/local/bin/python3

from __future__ import print_function
import sys
import os
import re
import io
import xml.etree.ElementTree as ET

def printElementText(parent,key,tag):
  elem = parent.find(tag)
  if elem is not None:
    if elem.text is not None:
      print(u'%s: "%s"' % (key,elem.text.strip()))

def printCategories(entry,key,tag):
  cnt = 0
  for elem in entry.findall(tag):
    term = elem.attrib['term']
    if term and term.find("#") < 0:
      if (not cnt):
        print(u"%s: %s" % (key,term),end="")
      else:
        print(u",%s" % term,end="")
      cnt = cnt + 1
  if cnt:
    print()

def multiline(text):
  for tag in ('p','li','ul','ol','div','blockquote'):
    text= re.sub("</"+tag+"><","</"+tag+">\n<",text)
  return text

def printMultilineText(entry,tag):
  elem = entry.find(tag)
  if elem is not None:
    print(multiline(elem.text))

def findLink(entry,tag,rel,type):
  for link in entry.findall(tag):
    if link.attrib['rel'] == rel and (link.attrib['type'] == type or type is None):
      return link.attrib['href']

def dumpEntryElements(entry):
  for elem in entry:
    print(elem.tag)
    print(elem.attrib)
    print("  ",elem.text)

def createOutputFile(url):
  m = re.search("//[a-zA-Z.]+/(.*)\\Z",url)
  if m is not None:
    path = m.group(1)
    if path:
      dir = os.path.dirname(path)
      if not os.path.exists(dir):
        os.makedirs(dir)
      print("Writing:",path)
      sys.stdout = io.open(path,mode="w")
      return path

def getEntryType(entry):
  for elem in entry.findall("{http://www.w3.org/2005/Atom}category"):
    if elem.attrib["scheme"] == "http://schemas.google.com/g/2005#kind":
      term = elem.attrib["term"]
      term = term.replace('http://schemas.google.com/blogger/2008/kind#',"")
      return term

def dumpBlog(root):
  cnt = 0
  comments = 0
  stdout = sys.stdout
  for entry in root:
    if entry.tag == "{http://www.w3.org/2005/Atom}entry":

      id = entry.find("{http://www.w3.org/2005/Atom}id")
      if id is not None:
        id_text = id.text
        if (id_text.find(".post") > 0):
          if (getEntryType(entry) == "post"):
            url = findLink(entry,"{http://www.w3.org/2005/Atom}link","alternate","text/html")
            if url:
              if createOutputFile(url):
                print(u"url: %s" % url)
                printElementText(entry,u"title","{http://www.w3.org/2005/Atom}title")
                printElementText(entry,u"published","{http://www.w3.org/2005/Atom}published")
                printCategories(entry,u"tag","{http://www.w3.org/2005/Atom}category")

                media = findLink(entry,"{http://www.w3.org/2005/Atom}link","enclosure",None)
                if media:
                  print(u"media: %s" % media)

                print()
                printMultilineText(entry,"{http://www.w3.org/2005/Atom}content")
                print()
                sys.stdout.close()
                sys.stdout = stdout
              else:
                sys.stderr.write("Cannot find file path in "+url)
            cnt = cnt + 1
          else:
            comments = comments + 1

#            dumpEntryElements(entry)

  print("Total: ",cnt,"blog posts and ",comments,"comments")
#
# Main code
#
if (len(sys.argv) == 0):
  print("Insufficient arguments, need input XML file")
  sys.exit()

print("Reading from ",sys.argv[1])

xml = ET.parse(sys.argv[1]);
root = xml.getroot();

dumpBlog(root)
