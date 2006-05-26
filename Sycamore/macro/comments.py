# -*- coding: iso-8859-1 -*-

from Sycamore import wikiutil, wikiform, config

#Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    text = []
    if args:
       title = args
    else:
       title = "Comments:"
    if not macro.request.user.may.edit(macro.formatter.page):
        text.append('<h3>%s</h3>\n<p><strong>Note: You must be logged in to add comments</strong></p>\n' % title)
    else: text.append('<h3>%s</h3>\n'
                '<form method="POST" action="%s/%s">\n'
                '<input type="hidden" name="action" value="comments">\n'
                '<input class="formfields" type="text" name="comment_text" size="75">\n'
                '<input type="hidden" name="button" value="Add Comment">\n'
                '<input class="formbutton" type="submit" name="button" value="Add Comment">\n'
                '</form>' % (title, macro.request.getScriptname(), macro.formatter.page.proper_name()))

    return formatter.rawHTML(''.join(text))
