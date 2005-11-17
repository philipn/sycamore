# -*- coding: iso-8859-1 -*-
"""
Map Macro
"""
from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page

def execute(macro, args):
    highlight = "Davis Area"
    if args:
       highlight = args
    retval = '<table cellspacing="0" cellpadding="0" width="810" height="460"><tr><td bgcolor="#ccddff" style="border: 1px dashed #aaaaaa;"><applet code="WikiMap.class" archive="%s/map.jar, %s/txp.jar" height=460 width=810 border="1"><param name="map" value="%s/map.xml"><param name="points" value="%s/points.xml"><param name="highlight" value="%s"><param name="wiki" value="/%s">You do not have Java enabled.</applet></td></tr></table>' % (config.web_dir, config.web_dir, config.web_dir, config.web_dir, highlight, config.relative_dir)
    return retval
