"""
This is just a support for Events.py so we can customized based on the lj's name.
"""

from LocalWiki import config

Dependencies = []

def execute(macro, args):
    if args:
        if config.relative_dir:
            htmltext = '<link rel=alternate type="application/rss+xml" href="/%s/Events_20Board?action=events&rss=1" title="RSS feed for DavisWiki Events Board">' % config.relative_dir +  '<p align="left"><a title="RSS 2.0" href="/%s/Events_20Board?action=events&rss=1" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a>&nbsp;&nbsp;<a title="LiveJournal" href="http://livejournal.com/~%s" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">LiveJournal</a>&nbsp;(<a href="/%s/Events_20Board_20Syndication">What are these?</a>)&nbsp;&nbsp;See also <a href="/%s/Regular_20Events">Regular Events</a>.</p>' % (config.relative_dir, args, config.relative_dir,config.relative_dir)
        else:
            htmltext = '<link rel=alternate type="application/rss+xml" href="/Events_Board?action=events&rss=1" title="RSS feed for DavisWiki Events Board"><p align="left"><a title="RSS 2.0" href="/Events_Board?action=events&rss=1" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a>&nbsp;&nbsp;<a title="LiveJournal" href="http://livejournal.com/~%s" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">LiveJournal</a>&nbsp;(<a href="/Events_Board_Syndication">What are these?</a>)&nbsp;&nbsp;See also <a href="/Regular_Events">Regular Events</a>.</p>' % args
    else:
        htmltext = 'Please provide an LJ name for the syndication feed.'
    return macro.formatter.rawHTML(htmltext)
