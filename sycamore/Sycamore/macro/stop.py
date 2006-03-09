Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    talkpagename = macro.formatter.page.page_name + '/Talk'
    text =  formatter.rawHTML('<center><div style="text-align: left; height: 32px; width: 400px; display: block; border: 1px solid #CBCBCB; padding: 2px;\
  font-size: 10px;"><img class="borderless" style="vertical-align:middle;padding-right: 10px; float:left;" src="%s"><div style="vertical-align: middle;">In an effort to promote a more open dialogue, discussion about the content of this page should continue at ' % macro.request.theme.img_url('stop.png'))
    text += formatter.pagelink(talkpagename) + '</div></div></center>'
    return text

