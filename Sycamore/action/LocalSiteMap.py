# -*- coding: iso-8859-1 -*-
"""
    Sycamore - LocalSiteMap action

    The LocalSiteMap action gives you a page that shows 
    nearby links.  This is an example of what appears on the 
    page (names are linkable on the real page):

    Sycamore
         GarthKidd
              OrphanedPages
              WantedPages
         JørnHansen
              CategoryHomepage
                   CategoryCategory
                   WikiHomePage
              JørnsTodo
              WikiWiki
                   OriginalWiki

    TODO:
        - add missing docs (docstrings, inline comments)

    @copyright: 2001 by Steve Howell <showell@zipcon.com>
    @copyright: 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""
    

"""
# Imports
from Sycamore import wikiutil
from Sycamore.Page import Page


def execute(pagename, request):
    _ = request.getText
    request.http_headers()
    wikiutil.send_title(request, _('Local Site Map for "%s"') % (pagename),  
        pagename=pagename)

    
    #caller = request.http_referer
    #if caller:
        #parts = urlparse.urlparse(caller)
        #request.write("Back to" + Page(parts[2].split("/")[-1]).link_to(request) +
        #              "<br><br>")

    request.write('<div id="content">\n') # start content div
    request.write(LocalSiteMap(pagename).output(request))
    request.write('</div>\n') # end content div
    wikiutil.send_footer(request, pagename)


class LocalSiteMap:
    def __init__(self, name):
        self.name = name
        self.result = []

    def output(self, request):
        tree = PageTreeBuilder(request).build_tree(self.name)
        #self.append("<small>")
        tree.depth_first_visit(request, self)
        #self.append("</small>")
        return ''.join(self.result)

    def visit(self, request, name, depth):
        # Visit a page, i.e. create a link.
        if not name: return
        self.append('&nbsp;' * (5*depth))
        self.append('&nbsp;' + wikiutil.link_tag(request, '%s?action=%s' %
            (wikiutil.quoteWikiname(name), __name__.split('.')[-1]), name))
        self.append("&nbsp;<small>[")
        self.append(Page(name).link_to(request, 'view'))
        self.append("</small>]<br>")

    def append(self, text):
        self.result.append(text)


class PageTreeBuilder:
    def __init__(self, request):
        self.request = request
        self.children = {}
        self.numnodes = 0
        self.maxnodes = 35

    def mark_child(self, name):
        self.children[name] = 1

    def child_marked(self, name):
        return self.children.has_key(name)

    def is_ok(self, child):
        if not self.child_marked(child):
            if not self.request.user.may.read(child):
                return 0
            if Page(child).exists():
                self.mark_child(child)
                return 1
        return 0

    def new_kids(self, name):
        # does not recurse
        kids = []
        for child in Page(name).getPageLinks(self.request):            
            if self.is_ok(child):
                kids.append(child)
        return kids        

    def new_node(self):
        self.numnodes = self.numnodes + 1
        if self.numnodes == self.maxnodes:
            raise "max nodes reached"

    def build_tree(self, name):
        self.mark_child(name)
        tree = Tree(name)
        try:
            self.recurse_build([tree], 1)
        except:
            pass
        return tree

    def recurse_build(self, trees, depth):
        all_kids = []
        for tree in trees:
            kids = self.new_kids(tree.node)
            for kid in kids:
                newTree = Tree(kid)
                tree.append(newTree)
                self.new_node()
                all_kids.append(newTree)
        if len(all_kids):
            self.recurse_build(all_kids, depth+1)

class Tree:
    def __init__(self, node):
        self.node = node
        self.children = []

    def append(self, node):
        self.children.append(node)
 
    def depth_first_visit(self, request, visitor, depth=0):
        visitor.visit(request, self.node, depth)
        for c in self.children:
            c.depth_first_visit(request, visitor, depth+1)

"""
