"""
    LocalWiki edit log class

    @license: GNU GPL, see COPYING for details.
"""

from logfile import LogFile
from LocalWiki import wikiutil, config, user, util
import os.path, string

"""
def editlog_replace_pagename(old,new):
    import re

    new_file = []
    l_file = open("/home/dwiki/public_html/dwiki/data/editlog","r")
    line = l_file.readline()
    while line:
       line = re.sub("%s\t" % old, new + "\t", line)
       new_file.append(line)
       line = l_file.readline()

    l_file.close()
    new_log = open("/home/dwiki/public_html/dwiki/data/editlog","w")
    for l in new_file:
       new_log.write(l)
    new_log.close()
"""

class EditLogLine:

    def __init__(self, usercache):
        self._usercache = usercache

    def __cmp__(self, other):
        try:
            return cmp(self.ed_time, other.ed_time)
        except AttributeError:
            return cmp(self.ed_time, other)

    def getEditorData(self, request):
        """ Return a tuple of type id and string or Page object
            representing the user that did the edit.

            The type id is one of 'ip' (DNS or numeric IP), 'user' (user name)
            or 'homepage' (Page instance of user's homepage).
        """
        result = ('ip', self.hostname)
        if self.userid:
            if not self._usercache.has_key(self.userid):
                self._usercache[self.userid] = user.User(request, self.userid)
            userdata = self._usercache[self.userid]
            if userdata.name:
                pg = wikiutil.getHomePage(request, username=userdata.name)
                if pg:
                    result = ('homepage', pg)
                else:
                    result = ('user', userdata.name)

        return result


    def getEditor(self, request):
        """ Return a HTML-safe string representing the user that did the edit.
        """
        kind, editor = self.getEditorData(request)
        ipString = wikiutil.escape(self.hostname)
        if kind == 'homepage':
            return '<span title="%s">%s</span>' % (ipString, editor.link_to(request))
        elif kind == 'ip':
            idx = editor.find('.')
            if idx==-1:
                idx = len(editor)
            return '<span title="%s">%s</span>' % (wikiutil.escape("%s=%s" % (self.addr,editor)), wikiutil.escape(editor[:idx]))
        else:
            return '<span title="%s">%s</span>' % (ipString, wikiutil.escape(editor))


class EditLog(LogFile):

    def __init__(self, filename=None, buffer_size=65536):
        if filename == None:
            filename = os.path.join(config.data_dir, 'editlog')
        LogFile.__init__(self, filename, buffer_size)
        self._NUM_FIELDS = 7
        self._usercache = {}

    def add(self, request, pagename, host, mtime, comment, action="SAVE"):
            """ Generate a line for the editlog.
    
            If `host` is None, it's read from request vars.
            """
            import socket
	    import os
	    import time

            #while os.path.exists("/home/dwiki/tmp.editlog_is_locked"):
	    #   time.sleep(0.2)
	     
            # lock the edit log (this is for the Rename action, for now)
            #f = open("/home/dwiki/tmp.editlog_is_locked","w")
            
            if not host:
                host = request.remote_addr
                
            # resolving the hostname was lagging the page edit screen
	    # for our actual event logging we're using noreq_add..
	    # NOTE:  IF WE WANT TO OPEN UP TO ANONYMOUS USERS THEN WE WILL NEED A WAY TO TURN ON HOSTNAME LOGGING JUST FOR THEM
            #try:
             #   hostname = socket.gethostbyaddr(host)[0]
            #except socket.error:
            #    hostname = host

            remap_chars = string.maketrans('\t\r\n', '   ')
            comment = comment.translate(remap_chars)

            line = "\t".join((wikiutil.quoteFilename(pagename), host,
                              repr(mtime), host,
                              request.user.valid and request.user.id or '',
                              comment, action)) + "\n"
            self._add(line)
	# this is insane!
	    #if (action == "SAVE" or action == "NEWEVENT"):
	    #	util.mail.sendmail(request, "5303042712@mobile.att.net",
           #	action, 
           #	"\"%s\",%s,%s" % (pagename, request.user.name, comment), mail_from="dwiki@daviswiki.org")
 
	    #while os.path.exists("/home/dwiki/tmp.editlog_replace_pagename"):
	    #  os.rename("/home/dwiki/tmp.editlog_replace_pagename","/home/dwiki/tmp.editlog_replace_pagename.2")
	    #  f = open("/home/dwiki/tmp.editlog_replace_pagename.2","r")
	    #  old_name = f.readline()
	    #  while old_name:
            #     new_name = f.readline()     
	    #     editlog_replace_pagename(old_name, new_name)
            #     old_name = f.readline()

            # unlock the editlog
            #f.close()
            #os.remove("/home/dwiki/tmp.editlog_is_locked")

    def noreq_add(self, request_remote_addr, request_user_valid, request_user_id, pagename, host, mtime, comment, action="SAVE"):
            """ Generate a line for the editlog.
            
            If `host` is None, it's read from request vars.
            """
            import socket
            import os
            import time

            #while os.path.exists("/home/dwiki/tmp.editlog_is_locked"):
            #   time.sleep(0.2)

            # lock the edit log (this is for the Rename action, for now)
            #f = open("/home/dwiki/tmp.editlog_is_locked","w")

            if not host:
                host = request_remote_addr

            #try:
            #    hostname = socket.gethostbyaddr(host)[0]
            #except socket.error:
            #    hostname = host

            remap_chars = string.maketrans('\t\r\n', '   ')
            comment = comment.translate(remap_chars)

            line = "\t".join((wikiutil.quoteFilename(pagename), host,
                              repr(mtime), host,
                              request_user_valid and request_user_id or '',
                              comment, action)) + "\n"
            self._add(line)
        # this is insane!
            #if (action == "SAVE" or action == "NEWEVENT"):
            #   util.mail.sendmail(request, "5303042712@mobile.att.net",
           #    action, 
           #    "\"%s\",%s,%s" % (pagename, request.user.name, comment), mail_from="dwiki@daviswiki.org")

            #while os.path.exists("/home/dwiki/tmp.editlog_replace_pagename"):
            #  os.rename("/home/dwiki/tmp.editlog_replace_pagename","/home/dwiki/tmp.editlog_replace_pagename.2")
            #  f = open("/home/dwiki/tmp.editlog_replace_pagename.2","r")
            #  old_name = f.readline()
            #  while old_name:
            #     new_name = f.readline()     
            #     editlog_replace_pagename(old_name, new_name)
            #     old_name = f.readline()

            # unlock the editlog
            #f.close()
            #os.remove("/home/dwiki/tmp.editlog_is_locked")

    def parser(self, line):
        fields = line.strip().split('\t')
        while len(fields) < self._NUM_FIELDS: fields.append('')
        result = EditLogLine(self._usercache)
        (result.pagename, result.addr, result.ed_time,
         result.hostname, result.userid, result.comment,
         result.action) = fields[:self._NUM_FIELDS]
        if not result.hostname:
            result.hostname = result.addr
        result.pagename = wikiutil.unquoteFilename(result.pagename)
        result.ed_time = float(result.ed_time or "0")
        if not result.action:
            result.action = 'SAVE'
        return result
    
    def set_filter(self, **kw):
        expr = "1"
        for field in ['pagename', 'addr', 'hostname', 'userid']:
            if kw.has_key(field):
                expr = "%s and x.%s == %s" % (expr, field, `kw[field]`)
                
        if kw.has_key('ed_time'):
            expr = "%s and int(x.ed_time) == %s" % (expr, int(kw['ed_time']))

        self.filter = eval("lambda x: " + expr)
    

