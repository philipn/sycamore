# -*- coding: utf-8 -*-
"""
    Sycamore - Info tab area rendering widget

    @copyright: 2006-2007 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2005 by David Reid
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import wikiutil
from Sycamore import config

from Sycamore.widget import base
from Sycamore.user import getUserId

def isNotSubscribed(request, page):
    return not request.user.isFavoritedTo(page) and request.user.valid

def isUserPage(request, page):
    if (config.user_page_prefix and
        page.page_name.startswith(config.user_page_prefix.lower())):
        username = page.page_name[len(config.user_page_prefix):]
        return getUserId(username, request)

class InfoBar(base.Widget):
    #format here is: Display, query args, should this be displayed
    infoTabs = [['Revision History', 'action=info', None, '&offset='],
                ['Links', 'action=info&links=1', None],
                # last "True" -> has sub-areas
                ['Files', 'action=Files', None, True], 
                ["User's Info", 'action=userinfo', isUserPage, '&offset=']
               ]

    before, after = '<li>', '</li>'
    before_active, after_active = '<li class="active">', '</li>'
    seperator = ' '

    def __init__(self, request, page):
        self.request = request
        self.page = page

    def render_link(self, tab):
        _ = self.request.getText

        if self.request.query_string == tab[1]:
            link = _(tab[0])
            self.request.write('%s%s%s' %
                               (self.before_active, link, self.after_active))

        elif (len(tab) == 4 and tab[3] and
              self.request.query_string.startswith(tab[1]) and
              (tab[3] is True or
               self.request.query_string[len(tab[1]):].startswith(tab[3]))):
            link = self.page.link_to(querystr=tab[1], text=_(tab[0]),
                                     know_status=True, know_status_exists=True)
            self.request.write('%s%s%s' %
                               (self.before_active, link, self.after_active))

        else:
            link = self.page.link_to(querystr=tab[1], text=_(tab[0]),
                                     know_status=True, know_status_exists=True)
            self.request.write('%s%s%s' % (self.before, link, self.after))

    def render(self):
        self.request.write('<ul id="tabmenu">')

        for tab in self.infoTabs:
            if callable(tab[2]):
                if not tab[2](self.request, self.page):
                    continue
            
            self.render_link(tab)
            self.request.write(self.seperator)
        
        self.request.write('</ul>')
