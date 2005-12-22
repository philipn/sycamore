# -*- coding: iso-8859-1 -*-

from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    text = []
    relative_dir = ''
    if config.relative_dir:
       relative_dir = '/' + config.relative_dir
    if args:
       title = args
    else:
       title = "Comments:"
    if not macro.request.user.valid:
        text.append('<h3>%s</h3>\n&nbsp;&nbsp;<strong>Note: You must be logged in to add comments</strong>\n' % title)
    else: text.append('<h3>%s</h3>\n'
                '<form method="POST" action="%s/%s">\n'
                '<input type="hidden" name="action" value="comments">\n'
                '<input class="formfields" type="text" name="comment_text" size="75">\n'
                '<input type="hidden" name="button" value="Add Comment">\n'
                '<input class="formbutton" type="submit" name="button" value="Add Comment">\n'
                '</form>' % (title, relative_dir, macro.formatter.page.page_name))

    return formatter.rawHTML(''.join(text))
