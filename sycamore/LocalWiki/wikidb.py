# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Wiki MySQL support functions

    @copyright: 2005 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from LocalWiki import config
import time
import MySQLdb

def connect():
  if config.db_user_password:
   db = MySQLdb.connect(host=config.db_host, user=config.db_user, db=config.db_name, password=config.db_password)
  else:
   db = MySQLdb.connect(host=config.db_host, user=config.db_user, db=config.db_name)

  return db

def cursor():
  return connect().cursor()
