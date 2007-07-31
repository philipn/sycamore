# -*- coding: utf-8 -*-

# Imports
from Sycamore import wikiutil
from Sycamore import config
from Sycamore import wikidb

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    macro.request.cursor.execute("""SELECT count(user_name)
                                    FROM userWikiInfo
                                    WHERE wiki_id=%(wiki_id)s and
                                          edit_count > 0""",
                                 {'wiki_id':macro.request.config.wiki_id})
    result = macro.request.cursor.fetchone()[0]
    return str(result)
