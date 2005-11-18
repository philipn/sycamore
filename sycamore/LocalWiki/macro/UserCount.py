# -*- coding: iso-8859-1 -*-
from LocalWiki import wikiutil, wikiform, config, wikidb
from LocalWiki.Page import Page

def execute(macro, args):
  db = wikidb.connect()
  cursor = db.cursor()
  cursor.execute("SELECT count(id) from users where id !='';")
  result = cursor.fetchone()[0]
  return str(result)
