# -*- coding: iso-8859-1 -*-
from Sycamore import wikiutil, wikiform, config, wikidb

def execute(macro, args, formatter=None):
  if not formatter: formatter = macro.formatter
  db = wikidb.connect()
  cursor = db.cursor()
  cursor.execute("SELECT count(user_name) from userWikiInfo where wiki_id=%(wiki_id)s", {'wiki_id':macro.request.config.wiki_id})
  result = cursor.fetchone()[0]
  return str(result)
