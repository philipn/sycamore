"""
This is just a support for Events.py so we can customized based on the lj's name.
"""

from Sycamore import config

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    if args:
         htmltext = '<link rel=alternate type="application/rss+xml" href="%sEvents_Board?action=events&rss=1" title="RSS feed for DavisWiki Events Board"><p align="left"><a title="RSS 2.0" href="%sEvents_Board?action=events&rss=1" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a>&nbsp;&nbsp;<a title="LiveJournal" href="http://livejournal.com/~%s" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">LiveJournal</a>&nbsp;(<a href="%sEvents_Board_Syndication">What are these?</a>)&nbsp;&nbsp;See also <a href="%sRegular_Events">Regular Events</a>.</p>' % (macro.request.getScriptname(), macro.request.getScriptname(), args, macro.request.getScriptname(), macro.request.getScriptname())
    else:
        htmltext = 'Please provide an LJ name for the syndication feed.'
    return formatter.rawHTML(htmltext)
