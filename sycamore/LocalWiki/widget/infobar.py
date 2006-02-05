from LocalWiki.widget import base
from LocalWiki.user import getUserId
from LocalWiki import wikiutil

def isNotSubscribed(request, pagename):
    return not request.user.isFavoritedTo(pagename) and request.user.valid

def isUserPage(request, pagename):
    return getUserId(pagename, request)

class InfoBar(base.Widget):
    #Display, query args, should this be displayed
    infoTabs = [['Revision History', 'action=info', None],
		['General Info', 'action=info&general=1', None],
		['Images', 'action=Files', None],
		["User's Edits", 'action=useredits', isUserPage],
		['Add to wiki bookmarks', 'action=favorite', isNotSubscribed]]

    before, after = '[', ']'
    seperator = ' '

    def __init__(self, request, pagename):
	self.request = request
	self.pagename = pagename

    def render_link(self, tab):
	_ = self.request.getText

	if self.request.query_string == tab[1]:
	    link = _(tab[0])
	else:
	    link = wikiutil.link_tag(self.request, 
				     '%s?%s' % (wikiutil.quoteWikiname(self.pagename), 
					       tab[1]), _(tab[0]))

	self.request.write(self.before + link + self.after)

    def render(self):
	self.request.write('<p>')

	for tab in self.infoTabs:
	    if callable(tab[2]):
		if not tab[2](self.request, self.pagename):
		    continue
	    
	    self.render_link(tab)
	    self.request.write(self.seperator)
	
	self.request.write('</p>')
