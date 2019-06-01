#!/usr/local/bin/python3

import yaml
import sys
import os
import argparse

def parseCLI():
  parser = argparse.ArgumentParser(description='Create S3 redirects')
  parser.add_argument('--redirect', dest='redirect', action='store', type=open, required=True,
                   help='Redirect YAML file')
  parser.add_argument('--bucket', dest='bucket', action='store', required=True,
                   help='Target S3 bucket')
  parser.add_argument('--index', dest='index', action='store', default='index.html',
                   help='Default HTML document')
  parser.add_argument('-v','--verbose', dest='verbose', action='store_true',
                   help='Increase verbosity')
  try:
    return parser.parse_args()
  except:
    sys.exit("Error parsing CLI parameters: "+str(sys.exc_info()[1]))

argv = parseCLI()
try:
  redirects = yaml.safe_load(argv.redirect)
except:
  print("Cannot read redirects",sys.exc_info()[1])
  sys.exit(1)

emptyname = "/tmp/empty-"+str(os.getpid())
if argv.verbose: print("Creating temporary empty file",emptyname)
with open(emptyname,"w") as file: file.close()

try:
  for (redir,target) in redirects.items():
    if redir.rfind('/') == len(redir) - 1:
      redir = redir + argv.index
    if argv.verbose: print("Creating redirect for",redir,"=>",target)
    exec = "aws s3 cp "+emptyname+" "+"s3://"+argv.bucket+redir+" --quiet --acl public-read --website-redirect "+redir
    if argv.verbose: print("Executing ",exec)
    stat = os.system(exec)
    if stat: sys.exit("AWS command failed with status %d " % stat)
finally:
  if argv.verbose: print("Cleanup: removing ",emptyname)
  os.remove(emptyname)
