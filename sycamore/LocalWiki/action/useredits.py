from LocalWiki import wikiutil, wikidb
from LocalWiki.widget.infobar import InfoBar
from LocalWiki.user import getUserId
from LocalWiki.Page import Page
from LocalWiki.util.dataset import TupleDataset, Column
from LocalWiki.widget.browser import DataBrowserWidget
from LocalWiki.formatter.text_html import Formatter

action_name = __name__.split('.')[-1]

def display_edits(request, userpage):
    def printNextPrev(request, pagename, last_edit, offset_given):
        #prints the next and previous links, if they're needed
	html = '<p>'
	if last_edit != 1:
	    html += '[<a href="%s/%s?action=useredits&offset=%s">previous edits</a> | ' % (request.getBaseURL(), pagename, offset_given+1)
	else:
	    html += '[previous edits | '
	if offset_given:
	    html += '<a href="%s/%s?action=useredits&offset=%s">next edits</a>]' % (request.getBaseURL(), pagename, offset_given-1) 
	else:
	    html += 'next edits]'
	html += '</p>'
	request.write(html)


    _ = request.getText

    edits = TupleDataset()
    edits.columns = [
	Column('page', label=_('Page')),
	Column('mtime', label=_('Date'), align='right'),
	Column('ip', label=_('From IP')),
	Column('comment', label=_('Comment')),
	Column('action', label=_('Action'))
    ]


    has_edits = False
    totalEdits = editedPages = 0

    this_edit = 0
    offset_given = int(request.form.get('offset', [0])[0])
    if not offset_given: 
	offset = 0
    else:
	offset = offset_given*100 - offset_given

    userid = getUserId(userpage)
    db = wikidb.connect()
    cursor = db.cursor()
    cursor.execute("SELECT count(editTime) from allPages where userEdited='%s'" % (userid,))
    count_result = cursor.fetchone()

    if count_result: 
	totalEdits = count_result[0]

    cursor.execute("SELECT count(DISTINCT name) from allPages where userEdited='%s'" % (userid,))
    count_result = cursor.fetchone()
    
    if count_result:
	editedPages = count_result[0]

    cursor.execute("SELECT name, editTime, userIP, editType, comment from allPages where userEdited='%s' order by editTime desc limit 100 offset %s" % (userid, offset))
    results = cursor.fetchall()
    cursor.close()
    db.close()

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

	page = Page(pagename)

	actions = ''

	actions = '%s&nbsp;%s' % (actions, page.link_to(request,
		     text=_('view'),
		     querystr='action=recall&amp;date=%s' % repr(mtime)))
	actions = '%s&nbsp;%s' % (actions, page.link_to(request,
		     text=_('raw'),
		     querystr='action=raw&amp;date=%s' % repr(mtime)))
	actions = '%s&nbsp;%s' % (actions, page.link_to(request,
		     text=_('print'),
		     querystr='action=print&amp;date=%s' % repr(mtime)))
	if request.user.may.revert(pagename) and editType != 'DELETE':
	    actions = '%s&nbsp;%s' % (actions, page.link_to(request,
			text=_('revert'),
                        querystr='action=revert&amp;date=%s&amp' % (repr(mtime))))

	if editType.find('/REVERT') != -1:
	    datestamp = request.user.getFormattedDateTime(float(comment))
	    comment = _("Revert to version dated %(datestamp)s.") % {'datestamp': datestamp}
	elif editType == 'ATTNEW':
	    comment = "Upload of attachment '%s.'" % comment
	elif editType == 'ATTDEL':
	    comment = "Attachment '%s' deleted." % comment
	elif editType == 'DELETE':
	    if comment: 
		comment = "Page deleted: '%s'" % comment
	    else: 
		comment = "Page deleted (no comment)"

	edits.addRow((page.link_to(request),
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

    wikiutil.simple_send_title(request, pagename, strict_title="User %s's Edit History" % pagename)

    request.write('<div id="content">\n\n')
    InfoBar(request, pagename).render()

    request.write('<h2>%s</h2>\n' % _("User's Edits"))

    display_edits(request, pagename)

    request.write('</div>')
    wikiutil.send_footer(request, pagename, showpage=1, noedit=True)
