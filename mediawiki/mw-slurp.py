#!/usr/local/bin/python3

import SlurpSite
import yaml
import sys
import argparse

def parseCLI():
  parser = argparse.ArgumentParser(description='Slurp a web file')
  parser.add_argument('--config', dest='config', action='store', default='slurp.yaml',
                   help='Configuration file')
  parser.add_argument('--report', dest='report', action='store', default=None,
                   help='Reporting format')
  parser.add_argument('--count', dest='count', type=int, action='store', default=None,
                   help='Maximum number of pages')
  parser.add_argument('--output', dest='output', action='store', default=None,
                   help='Output directory')
  return parser.parse_args()

def readConfig(fname,args):
  print("Using configuration file",fname)
  with open(fname) as stream:
    try:
      params = yaml.safe_load(stream)
    except:
      print("Cannot read slurp.yaml: ",sys.exc_info()[0])
      sys.exit(1)

  argv = vars(args)
  for a in argv:
    if argv[a] != None:
      params[a] = argv[a]

  return params

def reportLinks(site):
  for url in sorted(site):
    error = site[url].get('error',None)
    error = ' ('+str(error)+')' if error != None else ''
    redir = site[url].get('redirect',None)
    redir = ' ==> '+redir if redir != None else ''
    print(url+error+redir)

def reportStats(site):
  total  = 0
  error  = 0
  redir  = 0
  text   = 0
  binary = 0

  for url in sorted(site):
    total = total + 1
    if site[url].get('error'):
      error = error + 1
    if site[url].get('redirect'):
      redir = redir + 1
    if site[url].get('content'):
      if 'text' in site[url].get('content'):
        text = text + 1
      else:
        binary = binary + 1

  print('Slurp stats: %d pages (%d errors, %d redirects), %d text %d binary' % (total,error,redir,text,binary))

def reportSite(site,webparams):
  report = webparams.get('report')
  if report == 'links':
    reportLinks(site)
  else:
    reportStats(site)

def saveRedirects(site,webparams):
  redirects = {}
  for url in sorted(site):
    if site[url].get('redirect'):
      redirects[url] = site[url].get('redirect')

  with open(webparams['redirect'], 'w') as outfile:
    yaml.dump(redirects, outfile, default_flow_style=False)
    outfile.close()

args = parseCLI()
webparams = readConfig(args.config,args)

slurper = SlurpSite.SlurpSite(webparams)
slurper.setlog(webparams.get('logging',2))
site = slurper.Slurp(webparams.get("root","/"))

reportSite(site,webparams)
if webparams.get('redirect'):
  saveRedirects(site,webparams)
