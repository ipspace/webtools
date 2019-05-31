#!/usr/local/bin/python3

import SlurpSite
import yaml
import sys

with open('slurp.yaml') as stream:
  try:
    webparams = yaml.safe_load(stream)
  except:
    print("Cannot read slurp.yaml: ",sys.exc_info[0])
    sys.exit(1)

slurper = SlurpSite.SlurpSite(webparams)
slurper.setlog(webparams.get('logging',2))
site = slurper.Slurp("/")

for url in sorted(site):
  error = site[url].get('error',None)
  error = ' ('+str(error)+')' if error != None else ''
  print(url+error)
