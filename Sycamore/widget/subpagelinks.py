# This will take a string, such as "Front Page/Things to do/Fun stuff" and break it into logical subpage links. 

from Sycamore.widget import base
from Sycamore.Page import Page

class SubpageLinks(base.Widget):
    def __init__(self, request, pagename):
	self.pagename = pagename
	base.Widget.__init__(self, request)

    def _subpages(self):
        possible_subpages = self.pagename.split('/') 
        max_number_possible = len(possible_subpages)
        n = 1
        pagelinks = []
        pagenames_queue = []
        while n <= max_number_possible:
            pagename = possible_subpages[-n]
            parent_pagename = '/'.join(possible_subpages[:-n])
            if not parent_pagename:  # at end
                pagelinks.append((pagename, pagename))
            pagenames_queue.insert(0, pagename)
            if Page(parent_pagename, self.request).exists():
                display_pagename = '/'.join(pagenames_queue)
                pagenames_queue = []
                pagelinks.append(("%s/%s" % (parent_pagename, display_pagename), display_pagename))
            # tested all possible pagenames & we have no parent page that exists
            elif n == (max_number_possible-1) and len(pagenames_queue) == (max_number_possible-1):
                pagelinks = [(self.pagename, self.pagename)]
                break
            n += 1

        pagelinks.reverse()
        return pagelinks

    def render(self):
        """
        Returns a list of tuples [ .. (pagename, display_pagename), ... ] 
        """
	return self._subpages()
