# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Wiki MySQL support functions

    @copyright: 2005 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

# User calls wikidb.connect() to get a WikiDB object.

# Imports
from LocalWiki import config
import time
import MySQLdb

class WikiDB:
  def __init__(self, db):
    self.db = db

  def close(self):
    self.db.close()
  
  def cursor(self):
    return WikiDBCursor(self.db.cursor())

class WikiDBCursor:
  def __init__(self, db_cursor):
    self.db_cursor = db_cursor 

  
  def execute(self, query, args=None):
    if args: args = _fixArgs(args)
    self.db_cursor.execute(query, args) 

  def executemany(self, query, args):
    self.db_cursor.executemany(query, args)

  def fetchone(self):
    return self.db_cursor.fetchone()

  def fetchall(self):
    return self.db_cursor.fetchall()

  def close(self):
    return self.db_cursor.close()

def _fixArgs(args):
    # Converts python floats to limited-precision float strings
    #  before sending them to the db.  This is so that we can 
    #  keep the precision consistent between implementations.
    #  (I am not sure of a more elegant way to do this without using a specialized mysql type.)
    #  (This at least keeps consistency and keeps the accidential programmer from being throw off by 
    #  weird floating point issues)
    #  The idea is that we limit the length of our floats to be five places after the decimal point.
    #  Python's floats are bigger than this, and so are mysql's.  So we know that our internal rounding
    #  will work and be consistent between the two.

    def fixValue(o):
      if type(o) == type(float(1)): return _floatToString(o)
      else: return o
    
    # is args a sequence?
    if type(args) == type([]) or type(args) == type((1,)):
      args = map(fixValue, args)
    elif type(args) == type({}):
      for k, v in args.iteritems():
	 args[k] = fixValue(v) 
    else:
      args = fixValue(args)
        
    return args

def _floatToString(f):
  # converts a float to the proper length of double that mysql uses.
  # we need to use this when we render a link (GET/POST) that displays a double from the db, because python's floats are bigger than mysql's floats
  return "%.5f" % f

def connect():
  if config.db_user_password:
   db = MySQLdb.connect(host=config.db_host, user=config.db_user, db=config.db_name, password=config.db_password)
  else:
   db = MySQLdb.connect(host=config.db_host, user=config.db_user, db=config.db_name)

  return WikiDB(db)
