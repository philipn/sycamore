# -*- coding: iso-8859-1 -*-

from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page

#Dependencies = []

def execute(macro, args):
    text = []
    if args:
       title = args
    else:
       title = "Comments:"
    if not macro.request.user.valid:
        text.append('<h3>%s</h3>\n&nbsp;&nbsp;<strong>Note: You must be logged in to add comments</strong>\n' % title)
    else: text.append('<h3>%s</h3>\n'
                '<form method="POST" action="/%s/%s">\n'
                '<input type="hidden" name="action" value="comments">\n'
                '<input type="hidden" name="ticket" value="%s">\n'
                '<input class="formfields" type="text" name="comment_text" size="75">\n'
                '<input type="hidden" name="button" value="Add Comment">\n'
                '<input class="formbutton" type="submit" name="button" value="Add Comment">\n'
                '</form>' % (title, config.relative_dir, macro.formatter.page.page_name, createTicket()))

    return macro.formatter.rawHTML(''.join(text))

def createTicket(tm = None):
    """Create a ticket using a site-specific secret (the config)"""
    import sha, time, types
    ticket = tm or "%010x" % time.time()
    digest = sha.new()
    digest.update(ticket)

    cfgvars = vars(config)
    for var in cfgvars.values():
        if type(var) is types.StringType:
            digest.update(repr(var))

    return "%s.%s" % (ticket, digest.hexdigest())

