# -*- coding: iso-8859-1 -*-
from Sycamore import wikiutil, wikiform, config, wikidb

def execute(macro, args, formatter=None):
  if not formatter: formatter = macro.formatter
  db = wikidb.connect()
  cursor = db.cursor()
  cursor.execute("SELECT count(id) from users")
  result = cursor.fetchone()[0]
  return str(result)
