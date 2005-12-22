# -*- coding: iso-8859-1 -*-

from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    text = []
    if args:
       if args == "begin":
    	text.append('<center>')
       elif args == "end":
 	text.append('</center>')
    else:
       text.append('<b>You must supply the center macro with either "begin" or "end": i.e. [[center(begin)]] my centered text [[center(end)]]')

    return formatter.rawHTML(''.join(text))
