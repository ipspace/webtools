#!/usr/local/bin/python3

import SlurpSite

webparams = { "host" : "www.ipspace.net", "count" : 5 }

slurper = SlurpSite.SlurpSite(webparams)
slurper.setlog(3)
site = slurper.Slurp("/")

for url in sorted(site):
  print(url)
