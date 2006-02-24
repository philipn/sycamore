from LocalWiki import wikiutil, wikidb, user
from LocalWiki.widget.infobar import InfoBar
from LocalWiki.user import getUserId
from LocalWiki.Page import Page
from LocalWiki.util.dataset import TupleDataset, Column
from LocalWiki.widget.browser import DataBrowserWidget
from LocalWiki.formatter.text_html import Formatter
from LocalWiki.widget.comments import Comment

action_name = __name__.split('.')[-1]

def display_bookmarks(request, userpage):
  theuser = user.User(request, name=userpage)
  bookmarks = theuser.getFavoriteList()
  request.write('<div class="userFavoritesList">')
  for pagename in bookmarks:
    request.write('<span class="userFavoriteItem">%s</span>' % Page(pagename, request).link_to())
  request.write('</div>')
  

def display_edits(request, userpage):
    def printNextPrev(request, pagename, last_edit, offset_given):
        #prints the next and previous links, if they're needed
	html = ['<p>']
	if last_edit != 1:
	    html.append('[<a href="%s/%s?action=userinfo&offset=%s">&larr;previous edits</a> | ' % (request.getBaseURL(), pagename, offset_given+1))
	else:
	    html.append('[&larr;previous edits | ')
	if offset_given:
	    html.append('<a href="%s/%s?action=userinfo&offset=%s">next edits&rarr;</a>]' % (request.getBaseURL(), pagename, offset_given-1))
	else:
	    html.append('next edits&rarr;]')
	html.append('</p>')
	request.write(''.join(html))


    _ = request.getText

    edits = TupleDataset()
    edits.columns = [
	Column('page', label=_('Page')),
	Column('mtime', label=_('Date'), align='right'),
	Column('ip', label=_('From IP')),
	Column('comment', label=_('Comment')),
	Column('', label=_(''))
    ]


    has_edits = False
    totalEdits = editedPages = 0

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

    request.cursor.execute("SELECT name, editTime, userIP, editType, comment from allPages where userEdited=%(userid)s order by editTime desc limit 100 offset %(offset)s", {'userid':userid, 'offset':offset})
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

	page = Page(pagename, request)

	version = page.date_to_version_number(mtime)
	actions = page.link_to(text=_('show'), querystr='action=diff&amp;version2=%s&amp;version1=%s' % (version, version-1))
		     
	comment = Comment(request, comment, editType).render()

	edits.addRow((page.link_to(),
		      request.user.getFormattedDateTime(mtime),
		      userIp,
		      comment,
		      actions))
	count += 1
    
    if has_edits:
	request.write('<p>This user has made <b>%d</b> edits on <b>%d</b> pages.</p>' % (totalEdits, editedPages))

	request.write('<div id="useredits">')
	request.formatter = Formatter(request)
	edit_table = DataBrowserWidget(request)
	edit_table.setData(edits)
	edit_table.render()
	printNextPrev(request, userpage, this_edit, offset_given)
	request.write('</div>')
    else:
	request.write("<p>This user hasn't edited any pages.</p>")


def execute(pagename, request):
    _ = request.getText

    request.http_headers()

    wikiutil.simple_send_title(request, pagename, strict_title="User %s's information" % pagename)

    request.write('<div id="content">\n\n')
    InfoBar(request, pagename).render()

    request.write('<h2>Bookmarks</h2>\n')
    display_bookmarks(request, pagename)

    request.write('<h2>Edits</h2>\n')
    display_edits(request, pagename)

    request.write('</div>')
    wikiutil.send_footer(request, pagename, showpage=1, noedit=True)
