# -*- coding: iso8859-1 -*-
"""
    LocalWiki - Wiki XMLRPC v1 and v2 Interface
    
    Parts of this code are based on Jürgen Hermann's wikirpc.py,
    Les Orchard's "xmlrpc.cgi" and further work by Gustavo Niemeyer.

    See http://www.ecyrd.com/JSPWiki/Wiki.jsp?page=WikiRPCInterface
    and http://www.decafbad.com/twiki/bin/view/Main/XmlRpcToWiki
    for specs on many of the functions here.

    See also http://www.jspwiki.org/Wiki.jsp?page=WikiRPCInterface2
    for the new stuff.

    The main difference between v1 and v2 is that v2 relies on utf-8
    as transport encoding. No url-encoding and no base64 anymore, except
    when really necessary (like for transferring binary files like
    attachments maybe).

    @copyright: 2003-2004 by Thomas Waldmann
    @license: GNU GPL, see COPYING for details
"""

import sys, urllib, time, xmlrpclib

from LocalWiki import config, user, wikiutil
from LocalWiki.Page import Page
from LocalWiki.PageEditor import PageEditor
from LocalWiki.logfile import editlog

_debug = 0

class XmlRpcBase:
    def __init__(self, request):
        """
        Initialize an XmlRpcBase object.
        @param request: the request object
        """
        self.request = request
        self.version = None # this has to be defined in derived class

    #############################################################################
    ### Helper functions           
    #############################################################################

    def _instr(self, text):
        """
        Convert inbound string from utf-8.
        @param text: the text to convert
        @rtype: string
        @return: string in config.charset
        """
        raise "NotImplementedError"
    
    def _outstr(self, text):
        """
        Convert outbound string to utf-8.
        @param text: the text to convert
        @rtype: string
        @return: string in utf-8
        """
        raise "NotImplementedError"
    
    def _inlob(self, text):
        """
        Convert inbound base64-encoded utf-8 to Large OBject.
        @param text: the text to convert
        @rtype: string
        @return: string in config.charset
        """
        text = text.data
        if config.charset != 'utf-8':
            text = unicode(text, 'utf-8').encode(config.charset)
        return text

    def _outlob(self, text):
        """
        Convert outbound Large OBject to base64-encoded utf-8.
        @param text: the text to convert
        @rtype: string
        @return: xmlrpc Binary object
        """
        if config.charset != 'utf-8':
            text = unicode(text, config.charset).encode('utf-8')
        return xmlrpclib.Binary(text)
                    
    def _dump_exc(self):
        """ 
        Convert an exception to a string.
        @rtype: string
        @return: traceback as string
        """
        import traceback

        return "%s: %s\n%s" % (
            sys.exc_info()[0],
            sys.exc_info()[1],
            '\n'.join(traceback.format_tb(sys.exc_info()[2])),
        )


    #############################################################################
    ### Interface implementation
    #############################################################################

    def xmlrpc_getRPCVersionSupported(self):
        """
        Returns version of the Wiki API.
        @rtype: int
        @return: 1 or 2 (wikirpc version)
        """
        return self.version

    def xmlrpc_getAllPages(self):
        """
        get all pages
        @rtype: list
        @return: a list of all pages. The result is a list of utf-8 strings.
        """
        pagelist = wikiutil.getPageList(config.text_dir)
        pagelist = filter(self.request.user.may.read, pagelist)

        return map(self._outstr, pagelist)

    def xmlrpc_getRecentChanges(self, date):
        """
        get RecentChanges (since date)
        @param date: date since when rc will be listed
        @rtype: list
        @return: a list of changed pages since date, which should be in
            UTC. The result is a list, where each element is a struct:
            * name (string) :
                Name of the page. The name is in UTF-8.
            * lastModified (date) :
                Date of last modification, in UTC.
            * author (string) :
                Name of the author (if available). UTF-8.
            * version (int) :
                Current version.
        """
        
        return_items = []
        
        edit_log = editlog.EditLog()
        for log in edit_log.reverse():
            # get last-modified UTC (DateTime) from log
            gmtuple = tuple(time.gmtime(log.ed_time))
            lastModified_date = xmlrpclib.DateTime(gmtuple)

            # skip if older than "date"
            if lastModified_date < date:
                break
            
            # skip if knowledge not permitted
            if not self.request.user.may.read(log.pagename):
                continue
            
            # get page name (str) from log
            pagename_str = self._outstr(log.pagename)

            # get user name (str) from log
            author_str = log.hostname
            if log.userid:
                userdata = user.User(self.request, log.userid)
                if userdata.name:
                    author_str = userdata.name
            author_str = self._outstr(author_str)
            
            # get version# (int) from log
            # moin uses unix time as the page version number
            version_int = int(log.ed_time)

            return_item = { 'name':  pagename_str,
                            'lastModified': lastModified_date,
                            'author': author_str,
                            'version': version_int }
            return_items.append(return_item)
        
        return return_items

    def xmlrpc_getPageInfo(self, pagename):
        """
        get page information (latest version)
        @param pagename: the name of the page (utf-8)
        @rtype: list
        @return: page information
            * name (string): the canonical page name, UTF-8.
            * lastModified (date): Last modification date, UTC.
            * author (string): author name, UTF-8.
            * version (int): current version
        """
        return self.xmlrpc_getPageInfoVersion(pagename, None)

    def xmlrpc_getPageInfoVersion(self, pagename, version):
        """ 
        like getPageInfo(), but for a specific version.
        @param version: timestamp for version to get info about
        """
        pn = self._instr(pagename)
        if not self.request.user.may.read(pn):
            return xmlrpclib.Fault(1, "You are not allowed to read this page")

        if version != None:
            page = Page(pn, date=version)
        else:
            page = Page(pn)
        last_edit = page.last_edit(self.request)
        gmtuple = tuple(time.gmtime(last_edit['timestamp']))
        return { 'name': pagename,
                 'lastModified' : xmlrpclib.DateTime(gmtuple),
                 'author': self._outstr(str(last_edit['editor'])),
                 'version': int(last_edit['timestamp']),       # the timestamp is our "version"!
        }


    def xmlrpc_getPage(self, pagename):
        """
        Get the raw Wiki text of page (latest version)
        @param pagename: pagename (utf-8)
        @rtype: string
        @return: utf-8 encoded page data
        """    
        return self.xmlrpc_getPageVersion(pagename, None)


    def xmlrpc_getPageVersion(self, pagename, version):
        """
        same as getPage, but for specific version.
        @param version: timestamp
        """    
        pagename = self._instr(pagename)
        if not self.request.user.may.read(pagename):
            return xmlrpclib.Fault(1, "You are not allowed to read this page")

        if version != None:
            page = Page(pagename, date=version)
        else:
            page = Page(pagename)

        if self.version == 2:
            return self._outstr(page.get_raw_body())
        elif self.version == 1:
            return self._outlob(page.get_raw_body())

    def xmlrpc_getPageHTML(self, pagename):
        """
        get HTML of a page (latest version)
        @param pagename: the page name (utf-8)
        @rtype: string
        @return: page in rendered HTML (utf-8)
        """
        return self.xmlrpc_getPageHTMLVersion(pagename, None)

    def xmlrpc_getPageHTMLVersion(self, pagename, version):
        """
        same as getPageHTML, but for specific version
        @param version: timestamp
        """
        pagename = self._instr(pagename)
        if not self.request.user.may.read(pagename):
            return xmlrpclib.Fault(1, "You are not allowed to read this page")

        import cStringIO
        if version != None:
            page = Page(pagename, date=version)
        else:
            page = Page(pagename)

        out = cStringIO.StringIO()
        self.request.redirect(out)
        self.request.form = self.request.args = self.request.setup_args({})
        page.send_page(self.request, content_only=1)
        result = out.getvalue()
        self.request.redirect()

        if self.version == 2:
            return self._outstr(result)
        elif self.version == 1:
            return xmlrpclib.Binary(result)

    def xmlrpc_listLinks(self, pagename):
        """
        list links for a given page
        @param pagename: the page name
        @rtype: list
        @return: links of the page, structs, with the following elements
            * name (string) : The page name or URL the link is to, UTF-8 encoding.
            * type (int) : The link type. Zero (0) for internal Wiki
              link, one (1) for external link (URL - image link, whatever).
        """
        pagename = self._instr(pagename)
        if not self.request.user.may.read(pagename):
            return xmlrpclib.Fault(1, "You are not allowed to read this page")

        page = Page(pagename)

        links_out = []
        for link in page.getPageLinks(self.request):
            links_out.append({ 'name': self._outstr(link), 'type': 0 })
        return links_out


    def xmlrpc_putPage(self, pagename, pagetext):
        """
        save a page / change a page to a new text
        @param pagename: the page name (utf-8)
        @param pagetext: the new page text (content, utf-8)
        @rtype: bool
        @return: true on success
        """

        # we use a test page instead of using the requested pagename until
        # we have authentication set up - so nobody will be able to raid the wiki
        #pagename = _instr(pagename)
        pagename = "PutPageTestPage"

        # only authenticated (trusted) users may use putPage!
        # TODO: maybe replace this with an ACL right 'rpcwrite'
        if not (self.request.user.trusted and self.request.user.may.edit(pagename)):
            return xmlrpclib.Fault(1, "You are not allowed to edit this page")

        page = PageEditor(pagename, self.request)
        try:
            if self.version == 2:
                newtext = self._instr(pagetext)
            elif self.version == 1:
                newtext = self._inlob(pagetext)
            msg = page.saveText(newtext, "0")
        except page.SaveError, msg:
            pass
        if _debug and msg:
            sys.stderr.write("Msg: %s\n" % msg)

        #we need this to update pagelinks cache:
        import cStringIO
        out = cStringIO.StringIO()
        self.request.redirect(out)
        self.request.args = self.request.form = self.request.setup_args({})
        page.send_page(self.request, content_only=1)
        self.request.redirect()

        return xmlrpclib.Boolean(1)

    def plugincall(self, *args):
        return self.pluginfn(self, *args)

    def process(self):
        """
        xmlrpc v1 and v2 dispatcher
        """
        # read request
        data = self.request.read()

        params, method = xmlrpclib.loads(data)

        if _debug:
            sys.stderr.write('- XMLRPC ' + '-' * 70 + '\n')
            sys.stderr.write('%s(%s)\n\n' % (method, repr(params)))

        # generate response
        try:
            try:
                fn = getattr(self, 'xmlrpc_' + method)
            except AttributeError:
                self.pluginfn = wikiutil.importPlugin('xmlrpc', method, 'execute')
                fn = getattr(self, 'plugincall')
            response = fn(*params)
        except:
            # report exception back to server
            response = xmlrpclib.dumps(xmlrpclib.Fault(1, self._dump_exc()))
        else:
            # wrap response in a singleton tuple
            response = (response,)

            # serialize it
            response = xmlrpclib.dumps(response, methodresponse=1)

        self.request.http_headers([
            "Content-Type: text/xml; charset=utf-8",
            "Content-Length: %d" % len(response),
        ])
        self.request.write(response)

        if _debug:
            sys.stderr.write('- XMLRPC ' + '-' * 70 + '\n')
            sys.stderr.write(response + '\n\n')


class XmlRpc1(XmlRpcBase):
    def __init__(self, request):
        XmlRpcBase.__init__(self, request)
        self.version = 1

    def _instr(self, text):
        text = urllib.unquote(text)
        if config.charset != 'utf-8':
            text = unicode(text, 'utf-8').encode(config.charset)
        return text

    def _outstr(self, text):
        if config.charset != 'utf-8':
            text = unicode(text, config.charset).encode('utf-8')
        text = urllib.quote(text)
        return text

    
class XmlRpc2(XmlRpcBase):
    def __init__(self, request):
        XmlRpcBase.__init__(self, request)
        self.version = 2

    def _instr(self, text):
        if config.charset != 'utf-8':
            text = text.encode(config.charset)
            #This is not text = unicode(text, 'UTF-8').encode(config.charset)
            #because we already get unicode! Strange, but true...
        else:
            text = text.encode('utf-8')
            #as we obviously get unicode, we have to encode to utf-8 again
        return text

    def _outstr(self, text):
        if config.charset != 'utf-8':
            text = unicode(text, config.charset).encode('utf-8')
        return text

def xmlrpc(request):
    XmlRpc1(request).process()

def xmlrpc2(request):
    XmlRpc2(request).process()

