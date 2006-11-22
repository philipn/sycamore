from Sycamore import wikiutil, wikidb, user, config, farm
from Sycamore.widget.infobar import InfoBar
from Sycamore.user import getUserId
from Sycamore.Page import Page
from Sycamore.util.dataset import TupleDataset, Column
from Sycamore.widget.browser import DataBrowserWidget
from Sycamore.formatter.text_html import Formatter
from Sycamore.widget.comments import Comment

action_name = __name__.split('.')[-1]

def display_bookmarks(request, userpage):
  theuser = user.User(request, name=userpage)
  bookmarks = theuser.getFavorites()
  wiki_names = bookmarks.keys()
  # put current wiki in front of the rest
  if request.config.wiki_name in bookmarks:
    wiki_names.remove(request.config.wiki_name)
    wiki_names.insert(0, request.config.wiki_name)

  for wiki_name in wiki_names:
    if farm:
        request.write('<h3>%s</h3>' % farm.link_to_wiki(wiki_name, request.formatter))
    request.write('<div class="userFavoritesList">')
    for pagename in bookmarks[wiki_name]:
        request.write('<span class="userFavoriteItem">%s</span>' % Page(pagename, request, wiki_name=wiki_name).link_to())
    if farm:
        request.write('</div>')
  

def display_edits(request, userpage, on_pagename):
    def printNextPrev(request, pagename, last_edit, offset_given):
        #prints the next and previous links, if they're needed
        if last_edit == 1 and not offset_given: return 

        html = []
        if last_edit != 1:
            html.append('<div class="actionBoxes" style="margin-right:10px !important; float: left !important;"><span><a href="%s/%s?action=userinfo&offset=%s">&larr;previous edits</a></span></div>' % (request.getBaseURL(), pagename, offset_given+1))
        if offset_given:
            html.append('<div class="actionBoxes" style="float: left !important;"><span><a href="%s/%s?action=userinfo&offset=%s">next edits&rarr;</a></span></div>' % (request.getBaseURL(), pagename, offset_given-1))
        html.append('<div style="clear: both;"></div>')

        return [''.join(html)]


    _ = request.getText

    edits = TupleDataset()
    edits.columns = [
        Column('page', label=_('Page')),
        Column('mtime', label=_('Date'), align='right'),
        Column('ip', label=_('From IP')),
        Column('comment', label=_('Comment')),
    ]

    if config.wiki_farm:
        edits.columns.insert(1, Column('wiki', label=_('Wiki')))

    has_edits = False
    totalEdits = editedPages = 0
    editedWiki = 0

    this_edit = 0
    offset_given = int(request.form.get('offset', [0])[0])
    if not offset_given: 
        offset = 0
    else:
        offset = offset_given*100 - offset_given

    userid = getUserId(userpage, request)
    request.cursor.execute("SELECT count(editTime) from allPages where userEdited=%(userid)s", {'userid':userid})
    count_result = request.cursor.fetchone()

    if count_result: 
        totalEdits = count_result[0]

    request.cursor.execute("SELECT count(DISTINCT name) from allPages where userEdited=%(userid)s" , {'userid':userid})
    count_result = request.cursor.fetchone()
    
    if count_result:
        editedPages = count_result[0]

    request.cursor.execute("SELECT count(DISTINCT wiki_id) from allPages where userEdited=%(userid)s" , {'userid':userid})
    wiki_count_result = request.cursor.fetchone()
    if wiki_count_result:
        editedWikis = wiki_count_result[0]

    request.cursor.execute("SELECT allPages.name, allPages.editTime, allPages.userIP, allPages.editType, allPages.comment, wikis.name from allPages, wikis where allPages.userEdited=%(userid)s and wikis.id=allPages.wiki_id order by editTime desc limit 100 offset %(offset)s", {'userid':userid, 'offset':offset})
    results = request.cursor.fetchall()

    if results:
        has_edits = True
    
    count = 1
    for edit in results:
        this_edit = 1 + totalEdits - count - offset

        pagename = edit[0]
        mtime = edit[1]
        userIp = edit[2]
        editType = edit[3]
        comment = edit[4]
        wiki_name = edit[5]

        page = Page(pagename, request)

        version = page.date_to_version_number(mtime)
        show_page = page.link_to(querystr='action=diff&amp;version2=%s&amp;version1=%s' % (version, version-1))
                     
        comment = Comment(request, comment, editType).render()

        if config.wiki_farm:
            edits.addRow((show_page,
                          farm.link_to_wiki(wiki_name, request.formatter),
                          request.user.getFormattedDateTime(mtime),
                          userIp,
                          comment))
        else:
            edits.addRow((show_page,
                          request.user.getFormattedDateTime(mtime),
                          userIp,
                          comment))
        count += 1
    
    if has_edits:
        request.write('<p>This user has made <b>%d</b> edits to <b>%d</b> pages on <b>%s</b> wikis.</p>' % (totalEdits, editedPages, editedWikis))

        request.write('<div id="useredits">')
        edit_table = DataBrowserWidget(request)
        edit_table.setData(edits)
        edit_table.render(append=printNextPrev(request, on_pagename, this_edit, offset_given))
        request.write('</div>')
    else:
        request.write("<p>This user hasn't edited any pages.</p>")


def execute(pagename, request):
    _ = request.getText
    request.formatter = Formatter(request)
    page = Page(pagename, request)
    if not page.page_name.startswith(config.user_page_prefix.lower()):
        return page.send_page(msg="Not a user page.")
    username = pagename[len(config.user_page_prefix):]

    request.http_headers()

    wikiutil.simple_send_title(request, pagename, strict_title="User %s's information" % username)


    request.write('<div id="content" class="content">\n\n')
    InfoBar(request, page).render()
    request.write('<div id="tabPage">')

    request.write('<h3>Bookmarks</h3>\n')
    display_bookmarks(request, username)

    request.write('<h3>Edits</h3>\n')
    display_edits(request, username, pagename)

    request.write('</div></div>')
    wikiutil.send_footer(request, pagename, showpage=1, noedit=True)
