"""
    LocalWiki - VisualSiteMap action

    Idea is based on the webdot.py action.
    
    More or less redid it from scratch. Differs from the webdot action in several ways:
    * Uses the dot executable, not webdot, since webdot's not available on windows.
    * All links up to the search depth are displayed.
    * There's no maximal limit to the displayed nodes.
    * Nodes are marked during depth first visit, so each node is visited only once.
    * The visit method in class LocalSiteMap gets the whole tree as parameter. That way additional treenode information
      may be shown in the graph.
    * All edges between nodes contained in the graph are displayed, even if MAX_DEPTH is exceeded that way.
    * Optional depth controls
    * Nodes linked more then STRONG_LINK_NR times are highlighted using the STRONG_COLOR
    * Search depth is configurable
    
    Add this to your stylesheet:
    img.sitemap
    {
      border-width: 1;
      border-color: #000000;
    }

    07.10.2004
    * Maximum image size can be configured
    * Output image format is configurable
    * David Linke changed the output code (print() -> request.write())
    * Changed link counting algorithm to get the depth controls right.

    08.10.2004
    * IE caching problem with depth controls resolved. Now the current search depth is part of the file names.
    * Problems with pagenames containing non ASCII characters fixed.
    $Id$
"""

##################################################################
# Be warned that calculating large graphs may block your server! #   
# So be careful with the parameter settings.                     #
##################################################################

"""
# Imports
import string,sys,re,os
from LocalWiki import config, wikiutil, user
from LocalWiki.Page import Page

# Graph controls. 
DEFAULT_DEPTH = 6 
STRONG_LINK_NR = 4

# Optional controls for interactive modification of the search depth.
DEPTH_CONTROL = 0
MAX_DEPTH  = 6

# This should be a public path on your web server. The dot files, images and map files are created in this directory and
# served from there.
CACHE_DIR  = "/var/www/html/vismap";
CACHE_URL  = "http://82.165.250.53/vismap/";

# Absolute location of the dot (or neato) executable.
DOT_EXE    = "/usr/bin/dot";

# Desired image format (eg. png, jpg, gif - see the dot documentation)
OUTPUT_FORMAT = "png"

# Maximum output size in inches. Set to None to disable size limitation.
# OUTPUT_SIZE="8,4" sets maximum width to 8, maximum height to 4 inches.
OUTPUT_SIZE="None"

# Colors of boxes and edges.
BOX_COLOR  ="#E0F0FF"
ROOT_COLOR = "#FFE0E0"
STRONG_COLOR = "#E0FFE0"
EDGE_COLOR ="#888888"

# Categories are filtered in some way.
CATEGORY_STRING = "^Kategorie"

# Code starts here
def execute(pagename, request):
    _ = request.getText
    
    maxdepth = int(DEFAULT_DEPTH)
    if DEPTH_CONTROL and request.form.has_key('depth'):
      maxdepth = int(request.form['depth'][0])
    
    if int(maxdepth) > int(MAX_DEPTH):
      maxdepth = MAX_DEPTH
      
    request.http_headers()
    wikiutil.send_title(request, _('Visual Map of %s') % (pagename), pagename=pagename)

    baseurl = request.getBaseURL()

    wikiname = wikiutil.quoteWikiname(pagename)
    dotfilename = '%s/%s_%s.dot' % (CACHE_DIR, wikiname, maxdepth)
    imagefilename = '%s/%s_%s.%s' % (CACHE_DIR, wikiname, maxdepth, OUTPUT_FORMAT)
    imageurl = '%s/%s_%s.%s' % (CACHE_URL, wikiname, maxdepth, OUTPUT_FORMAT)
    mapfilename = '%s/%s_%s.cmap' % (CACHE_DIR, wikiname, maxdepth)

    dotfile = open(dotfilename,'w')
    
    dotfile.write('digraph G {\n')
    if OUTPUT_SIZE:
        dotfile.write('  size="%s"\n' % OUTPUT_SIZE)
        dotfile.write('  ratio=compress;\n')
    dotfile.write('  URL="%s";\n' % wikiname)
    dotfile.write('  overlap=false;\n')
    dotfile.write('  concentrate=true;\n')
    dotfile.write('  edge [color="%s"];\n' % EDGE_COLOR)
    dotfile.write('  node [URL="%s/\N", ' % baseurl)
    dotfile.write('fontcolor=black, fontname=%s , fontsize=%s, style=filled, color="%s"]\n' % ("arial","8", BOX_COLOR))
    dotfile.write(LocalSiteMap(pagename, maxdepth).output(request))
    dotfile.write('}\n')
    dotfile.close()
    
    os.system('%s -T%s -o%s %s' % (DOT_EXE, OUTPUT_FORMAT, imagefilename, dotfilename))
    os.system('%s -Tcmap -o%s %s' % (DOT_EXE, mapfilename, dotfilename))
   
    request.write('<center><img class="sitemap" border=1 src="%s" usemap="#map1"></center>' % (imageurl))
    request.write('<map name="map1">')
    mapfile = open(mapfilename,'r')
    for row in mapfile.readlines():
        request.write(row)
    mapfile.close()
      
    request.write('</map>')
    
    if DEPTH_CONTROL:
      linkname = wikiutil.quoteWikiname(pagename)
      request.write('<p align="center">')
      if maxdepth > 1:
          request.write('<a href="%s/%s?action=VisualSiteMap&depth=%s">Less</a>' % (baseurl, linkname, maxdepth-1))
      else:
          request.write('Less')

      request.write(' | ')

      if maxdepth < MAX_DEPTH:
          request.write('<a href="%s/%s?action=VisualSiteMap&depth=%s">More</a>' % (baseurl, linkname, maxdepth+1))
      else:
          request.write('More')
      request.write('</p>')
      
    request.write('<p align="center"><small>Search depth is %s. Nodes linked more than %s times are highlighted.</small></p>' % (maxdepth, STRONG_LINK_NR))

    wikiutil.send_footer(request, pagename)

class LocalSiteMap:
    def __init__(self, name, maxdepth):
        self.name = name
        self.result = []
        self.maxdepth = maxdepth

    def output(self, request):
        pagebuilder = GraphBuilder(request, self.maxdepth)
        root = pagebuilder.build_graph(self.name)
        # count links
        # print '<h2> All links </h2>'
        for edge in pagebuilder.all_edges:
            edge[0].linkedfrom += 1
            edge[1].linkedto += 1
            # print edge[0].name + '->' + edge[1].name + '<BR>'
        # write nodes
        for node in pagebuilder.all_nodes:
            self.append('  %s'% wikiutil.quoteWikiname(node.name))
            if node.depth > 0:
                if node.linkedto >= STRONG_LINK_NR:
                    self.append('  [label="%s",color="%s"];\n' % (node.name, STRONG_COLOR))
                else:
                    self.append('  [label="%s"];\n' % (node.name))

            else:
                self.append('[label="%s",shape=box,style=filled,color="%s"];\n' % (node.name, ROOT_COLOR))
        # write edges
        for edge in pagebuilder.all_edges:
            self.append('  %s->%s;\n' % (wikiutil.quoteWikiname(edge[0].name),wikiutil.quoteWikiname(edge[1].name)))
            
        return string.join(self.result, '')

    def append(self, text):
        self.result.append(text)


class GraphBuilder:
    
    def __init__(self, request, maxdepth):
        self.request = request
        self.maxdepth = maxdepth
        self.all_nodes = []
        self.all_edges = []
        
    def is_ok(self, child):
        if not self.request.user.may.read(child):
            return 0
        if Page(child).exists() and (not re.search(r'%s' % CATEGORY_STRING,child)):
            return 1
        return 0

    def build_graph(self, name):
        # Reuse generated trees
        nodesMap = {}
        root = Node(name)
        nodesMap[name] = root
        root.visited = 1
        self.all_nodes.append(root)
        self.recurse_build([root], 1, nodesMap)
        return root

    def recurse_build(self, nodes, depth, nodesMap):
        # collect all nodes of the current search depth here for the next recursion step
        child_nodes = []
        # iterate over the nodes
        for node in nodes:
            # print "<h2>%s: Kids of %s</h2>" % (depth,node.name)
            for child in Page(node.name).getPageLinks(self.request):            
                if self.is_ok(child):
                    # print "Child %s" % child
                    # Create the node with the given name
                    if not nodesMap.has_key(child):
                        # create the new node and store it
                        newNode = Node(child)
                        newNode.depth = depth
                        # print "is new"
                    else:
                        newNode = nodesMap[child]
                        # print "is old"
                    # print ". <br>"
                    # If the current depth doesn't exceed the maximum depth, add newNode to recursion step
                    if (int(depth) <= int(self.maxdepth)):
                        # The node is appended to the nodes list for the next recursion step.
                        nodesMap[child] = newNode
                        self.all_nodes.append(newNode)
                        child_nodes.append(newNode)
                        node.append(newNode)
                        # Draw an edge.
                        edge = (node, newNode)
                        if (not edge in self.all_edges):
                            self.all_edges.append(edge)
        # recurse, if the current recursion step yields children
        if len(child_nodes):
            self.recurse_build(child_nodes, depth+1, nodesMap)

class Node:
    def __init__(self, name):
        self.name = name
        self.children = []
        self.visited = 0
        self.linkedfrom = 0
        self.linkedto = 0
        self.depth = 0
        
    def append(self, node):
        self.children.append(node)
"""
