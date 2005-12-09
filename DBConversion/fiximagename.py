#!/usr/bin/python
import urllib, sys

def fixImageName(filename):
  unquoted = urllib.unquote(filename)
  unquoted = unquoted.replace('<', '')
  unquoted = unquoted.replace('>', '')
  unquoted = unquoted.replace('&', '')
  unquoted = unquoted.replace('"', '')
  unquoted = unquoted.replace('?', '')
  return unquoted

print fixImageName(sys.argv[1])
