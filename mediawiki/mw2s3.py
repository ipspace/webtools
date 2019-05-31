#!/usr/local/bin/python3

import SlurpSite
import yaml
import sys
import argparse

def parseCLI():
  parser = argparse.ArgumentParser(description='Slurp a web file')
  parser.add_argument('--config', dest='config', action='store', default='slurp.yaml',
                   help='Configuration file')
  return parser.parse_args()

def readConfig(fname):
  print("Using configuration file",fname)
  with open(fname) as stream:
    try:
      return yaml.safe_load(stream)
    except:
      print("Cannot read slurp.yaml: ",sys.exc_info[0])
      sys.exit(1)

args = parseCLI()
webparams = readConfig(args.config)

slurper = SlurpSite.SlurpSite(webparams)
slurper.setlog(webparams.get('logging',2))
site = slurper.Slurp(webparams.get("root","/"))

for url in sorted(site):
  error = site[url].get('error',None)
  error = ' ('+str(error)+')' if error != None else ''
  print(url+error)
