# -*- coding: iso-8859-1 -*-

from Sycamore import wikiutil, wikiform, config

#Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    macro.parser.inhibit_br += 2
    text = []
    if args:
       title = args
    else:
       title = "Comments:"
    if not macro.request.user.may.edit(macro.formatter.page):
        text.append('<h3>%s</h3>\n<p><strong>Note: You must be logged in to add comments</strong></p>\n' % title)
    else:
        text.append('<h3>%(title)s</h3>\n'
                '<form method="POST" action="%(scriptname)s/%(pagename)s">\n'
                '<p><input type="hidden" name="action" value="comments">\n'
                '<textarea id="comment_text" name="comment_text" rows="1" style="width:100%%" onSelect="sizeTextField(this.id,event)" onPaste="sizeTextField(this.id,event)" onFocus="sizeTextField(this.id,event)" onKeyPress="sizeTextField(this.id,event)"></textarea>\n'
                '<input type="hidden" name="button" value="Add Comment">\n'
                '<input class="formbutton" type="submit" name="button" value="Add Comment"></p>\n'
                '</form>' % {'title': title, 'scriptname': macro.request.getScriptname(), 'pagename': macro.formatter.page.proper_name()})

    # we want to print a paragraph after the comments area if there's anything following it
    macro.parser.force_print_p = True

    return formatter.rawHTML(''.join(text))
