from LocalWiki.Page import Page
#Dependencies = []

def execute(macro, args):
    talkpagename ="Talk:" + macro.formatter.page.page_name
    talkpage = Page(talkpagename)
    text =  macro.formatter.rawHTML('<center><div style="text-align: left; height: 32px; width: 400px; display: block; border: 1px solid #CBCBCB; padding: 2px;\
  font-size: 10px;"><img class="borderless" style="vertical-align:middle;padding-right: 10px; float:left;" src="/stop.png"><div style="vertical-align: middle;">In an effort to promote a more open dialogue, discussion about the content of this page should continue at ')
    text += (talkpage.link_to(macro.request, talkpagename) + '</div></div></center>')
    return text

