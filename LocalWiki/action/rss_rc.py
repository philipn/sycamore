"""
    RSS Handling

    If you do changes, please check if it still validates after your changes:

    http://feedvalidator.org/

    @license: GNU GPL, see COPYING for details.
"""
import StringIO, re, os, string
from LocalWiki import wikixml, config, wikiutil, util
from LocalWiki.logfile import editlog
from LocalWiki.Page import Page
from LocalWiki.wikixml.util import RssGenerator

def execute(pagename, request):
    """ Send recent changes as an RSS document
    """
    if not wikixml.ok:
        #XXXX send error message
        pass

    # get params
    items_limit = 100
    try:
        max_items = int(request.form['items'][0])
        max_items = min(max_items, items_limit) # not more than `items_limit`
    except (KeyError, ValueError):
        # not more than 15 items in a RSS file by default
        max_items = 15
    try:
        unique = int(request.form.get('unique', [0])[0])
    except ValueError:
        unique = 0
    try:
        diffs = int(request.form.get('diffs', [0])[0])
    except ValueError:
        diffs = 0
    ## ddiffs inserted by Ralf Zosel <ralf@zosel.com>, 04.12.2003
    try:
        ddiffs = int(request.form.get('ddiffs', [0])[0])
    except ValueError:
        ddiffs = 0

    # prepare output
    out = StringIO.StringIO()
    handler = RssGenerator(out)

    # get data
    interwiki = request.getBaseURL()
    if interwiki[-1] != "/":
        interwiki += "/"

    logo = re.search(r'src="([^"]*)"', config.logo_string)
    if logo:
        logo = request.getQualifiedURL(logo.group(1))
    
    log = editlog.EditLog()
    logdata = []
    counter = 0
    pages = {}
    for line in log.reverse():
        if not request.user.may.read(line.pagename):
            continue
        if ((line.action[:4] != 'SAVE') or
            (line.pagename in pages)): continue
        #if log.dayChanged() and log.daycount > _MAX_DAYS: break
        line.editor = line.getEditorData(request)[1]
        line.time = util.datetime.tmtuple(line.ed_time) # UTC
        logdata.append(line)
        pages[line.pagename] = None
        counter += 1
        if counter >= max_items:
            break
    del log
            
    # start SAX stream
    handler._out.write(
        '<?xml version="1.0" ?>'
        '<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">'
        )
    handler._out.write(
        '<!--\n'
        '    Add an "items=nnn" URL parameter to get more than the default 15 items.\n'
        '    You cannot get more than %d items though.\n'
        '    \n'
        '    Add "unique=1" to get a list of changes where page names are unique,\n'
        '    i.e. where only the latest change of each page is reflected.\n'
        '    \n'
        '    Add "diffs=1" to add change diffs to the description of each items.\n'
        '    \n'
        '    Add "ddiffs=1" to link directly to the diff (good for FeedReader).\n'
        '-->\n' % items_limit
        )

    # emit channel description
    relative_dir = ''
    if config.relative_dir:
        relative_dir = '/' + config.relative_dir
    handler._out.write(
        '<channel>'
        '<title>Recent Changes</title>'
        '<link>http://%s%s/Recent_Changes</link>'
        '<description>Davis Wiki Recent Changes</description>'
        '<language>en-us</language>'
        % (config.domain, relative_dir)
        )

    # emit items
    for item in logdata:
        page = Page(item.pagename)
        link = interwiki + wikiutil.quoteWikiname(item.pagename)
        rdflink = "%s#%04d%02d%02d%02d%02d%02d" % ((link,) + item.time[:6])
        handler._out.write('<item>')
        # general attributes
        handler._out.write('<title>%s</title>' % string.replace(item.pagename, "&", "&amp;"))
        if ddiffs:
            handler.simpleNode('link', link+"?action=diff")
        else:
            handler.simpleNode('link', link)
        handler._out.write('<dc:date>%s</dc:date>' % util.W3CDate(item.time))   

        # description
        desc_text = unicode(item.comment,config.charset).encode('ascii','replace')
        if diffs:
            # !!! TODO: rewrite / extend wikiutil.pagediff
            # searching for the matching pages doesn't really belong here
            # also, we have a problem to get a diff between two backup versions
            # so it's always a diff to the current version for now
            oldversions = wikiutil.getBackupList(config.backup_dir, item.pagename)

            for idx in range(len(oldversions)):
                oldpage = oldversions[idx]
                try:
                    date = os.path.getmtime(os.path.join(config.backup_dir, oldpage))
                except EnvironmentError:
                    continue
                if date <= item.ed_time:
                    if idx+1 < len(oldversions):
                        file1 = os.path.join(config.backup_dir, oldversions[idx+1])
                        file2 = page._text_filename()
                        rc, page_file, backup_file, lines = wikiutil.pagediff(file1, file2, ignorews=1)
                        if len(lines) > 20: lines = lines[20:] + ['...\n']
                        desc_text = desc_text + '<pre>\n' + ''.join(lines) + '</pre>'
                    break
        if desc_text:
            handler.simpleNode('description', desc_text)

        # contributor
        edattr = {}
        if isinstance(item.editor, Page):
            edname = item.editor.page_name
            ##edattr[(None, 'link')] = interwiki + wikiutil.quoteWikiname(edname)
        else:
            edname = item.editor
            ##edattr[(None, 'link')] = link + "?action=info"
        
        # this edattr stuff, esp. None as first tuple element breaks things (tracebacks)
        # if you know how to do this right, please send us a patch
        
        handler._out.write('<dc:creator>')
        handler._out.write(edname)
        handler._out.write('</dc:creator>')

        # wiki extensions
	# i turned these off because of rss parse errors

        # handler.simpleNode(('wiki', 'importance'), ) # ( major | minor ) 
        # handler.simpleNode(('wiki', 'version'), ) # ( #PCDATA ) 

        handler._out.write('</item>')
        
    handler._out.write('</channel>')
    # end SAX stream
    handler._out.write('</rss>')

    # send the generated XML document
    request.http_headers(["Content-Type: text/xml"] + request.nocache)
    request.write(out.getvalue())
    request.finish()
    request.no_closing_html_code = 1
    
