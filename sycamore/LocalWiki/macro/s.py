# -*- coding: iso-8859-1 -*-

from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page

Dependencies = []

def execute(macro, args):
    text = []
    if args:
       if args == "begin" or args == "start":
          text.append('<s>')
       elif args == "end" or args == "stop":
          text.append('</s>')
    else:
       text.append('<b>You must supply the strike-through macro with either "begin" or "end": i.e. [[s(begin)]] my striked-through text [[s(end)]]')

    return macro.formatter.rawHTML(''.join(text))
