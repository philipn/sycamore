# -*- coding: iso-8859-1 -*-
"""
Map Macro
"""
from Sycamore import config

Dependencies = []

def execute(macro, args, formatter=None):
    return ''
    #if not formatter: formatter = macro.formatter
    #highlight = "Davis Area"
    #if args:
    #   highlight = args
    #retval = '<table cellspacing="0" cellpadding="0" width="810" height="460"><tr><td bgcolor="#ccddff" style="border: 1px dashed #aaaaaa;"><applet code="WikiMap.class" archive="%s/wiki/map.jar" height=460 width=810 border="1"><param name="map" value="%s/wiki/map.xml"><param name="points" value="%s/Map?action=mapPointsXML"><param name="highlight" value="%s"><param name="wiki" value="%s">You do not have Java enabled.</applet></td></tr></table>' % (config.web_dir, config.web_dir, macro.request.getScriptname(), highlight, macro.request.getScriptname())
    #return retval
