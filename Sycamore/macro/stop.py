Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    talkpagename = macro.formatter.page.proper_name() + '/Talk'
    text =  formatter.rawHTML('<center><table style="border: 1px solid #CBCBCB; width: 400px; font-size: x-small;"><tr><td style="padding: 2px;">%s</td><td style="padding: 2px;">In an effort to promote a more open dialogue, discussion about the content of this page should continue at %s</td></tr></table></center>' % (macro.request.theme.make_icon('stop.png'), formatter.pagelink(talkpagename)))
    return text

