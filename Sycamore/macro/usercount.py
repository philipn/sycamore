# -*- coding: iso-8859-1 -*-
from Sycamore import wikiutil, config, wikidb

def execute(macro, args, formatter=None):
  if not formatter: formatter = macro.formatter
  macro.request.cursor.execute("SELECT count(user_name) from userWikiInfo where wiki_id=%(wiki_id)s and edit_count > 0", {'wiki_id':macro.request.config.wiki_id})
  result = macro.request.cursor.fetchone()[0]
  return str(result)
