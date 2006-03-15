from Sycamore.widget import base
from Sycamore.user import getUserId
from Sycamore import wikiutil

def isNotSubscribed(request, pagename):
    return not request.user.isFavoritedTo(pagename) and request.user.valid

def isUserPage(request, pagename):
    return getUserId(pagename, request)

class InfoBar(base.Widget):
    #Display, query args, should this be displayed
    infoTabs = [['Revision History', 'action=info', None],
		['General Info', 'action=info&general=1', None],
		['Images', 'action=Files', None],
		["User's Info", 'action=userinfo', isUserPage],
		['Add to wiki bookmarks', 'action=favorite', isNotSubscribed]]

    before, after = '<li>', '</li>'
    before_active, after_active = '<li class="active">', '</li>'
    seperator = ' '

    def __init__(self, request, pagename):
	self.request = request
	self.pagename = pagename

    def render_link(self, tab):
	_ = self.request.getText

	if self.request.query_string == tab[1]:
	    link = _(tab[0])
	    self.request.write('%s%s%s' % (self.before_active, link, self.after_active))

	else:
	    link = wikiutil.link_tag(self.request, 
				     '%s?%s' % (wikiutil.quoteWikiname(self.pagename), 
					       tab[1]), _(tab[0]))

	    self.request.write('%s%s%s' % (self.before, link, self.after))

    def render(self):
	self.request.write('<ul id="tabmenu">')

	for tab in self.infoTabs:
	    if callable(tab[2]):
		if not tab[2](self.request, self.pagename):
		    continue
	    
	    self.render_link(tab)
	    self.request.write(self.seperator)
	
	self.request.write('</ul>')
