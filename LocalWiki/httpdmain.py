# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Stand-alone HTTP Server

    You can use this for private, single-user wikis (like when installing on
    your private PC or notebook).
    
    Usage for public wikis with multiple users is not recommended, use cgi,
    fastcgi or twisted in that case.
    
    @copyright: 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.

    Significant contributions to this module by R. Church <rc@ghostbitch.org>
"""

# Imports
import os, signal, sys, time, thread, urllib
import BaseHTTPServer, SimpleHTTPServer
from LocalWiki import config, version
from LocalWiki.request import RequestStandAlone
from email.Utils import formatdate
    
allowed_extensions = ['.gif', '.jpg', '.png', '.css', '.js']

httpd = None
    
# Classes
class MoinServer(BaseHTTPServer.HTTPServer):
    def __init__(self, server_address, htdocs):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, MoinRequestHandler)

        self.htdocs = htdocs
        self._abort = 0

    def serve_in_thread(self):
        """Start the main serving loop in its own thread."""
        thread.start_new_thread(self.serve_forever, ())

    def serve_forever(self):
        """Handle one request at a time until we die."""
        sys.stderr.write("Serving on %s:%d, documents in '%s'\n" % (self.server_address + (self.htdocs,)))
        while not self._abort:
            self.handle_request()

    def die(self):
        """Abort this server instance's serving loop."""
        self._abort = 1

        # make request to self so server wakes up
        import httplib
        req = httplib.HTTP('%s:%d' % self.server_address)
        req.connect()
        req.putrequest('DIE', '/')
        req.endheaders()
        del req


class MoinRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    server_version = "LocalWiki/" + version.revision

    def __init__(self, request, client_address, server):
        self.expires = 0
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_DIE(self):
        if self.server._abort:
            self.log_error("Shutting down")

    def do_POST(self):
        self.doRequest()

    def do_GET(self):
        path = self.path
        if '?' in path:
            index = path.find('?')
            path = path[:index]
        dummy, extension = os.path.splitext(path)
        # XXX FIXME it might be a bit too simple to just use the extension to decide if
        # we should call the static server or get a wiki page. As long as wiki page URLs
        # translate ".png" -> "_2Epng" (if anybody makes such a strange page), this is no
        # problem, though.
        if extension.lower() in allowed_extensions:
            self.expires = 7*24*3600 # 1 week expiry for png, css
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.doRequest()

    def translate_path(self, uri):
        """ Translate a /-separated PATH to the local filename syntax.

            Components that mean special things to the local file system
            (e.g. drive or directory names) are ignored.

        """
        file = urllib.unquote(uri)
        file.replace('\\', '/')
        words = file.split('/')
        words = filter(None, words)

        path = self.server.htdocs
        bad_uri = 0
        for word in words:
            drive, word = os.path.splitdrive(word)
            if drive:
                bad_uri = 1
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                bad_uri = 1
                continue
            path = os.path.join(path, word)

        if bad_uri:
            self.log_error("Detected bad request URI '%s', translated to '%s'" % (uri, path,))
            
        return path

    def end_headers(self):
        """overload the default end_headers, inserting expires header"""
        if self.expires:
            now = time.time()
            expires = now + self.expires
            self.send_header('Expires', formatdate(expires))
        SimpleHTTPServer.SimpleHTTPRequestHandler.end_headers(self)
        
    def doRequest(self):
        """Serve a request."""
        self.expires = 0 # don't make an Expires header for wiki pages
        self.send_response(200)
        req = RequestStandAlone(self)
        req.run()


# Functions
def quit(signo, stackframe):
    """Signal handler for aborting signals."""
    global httpd
    print "Interrupted!"
    if httpd: httpd.die()
    #sys.exit(0)

def run():
    # set globals (only on first import, save from reloads!)
    global httpd

    # register signal handler
    signal.signal(signal.SIGABRT, quit)
    signal.signal(signal.SIGINT,  quit)
    signal.signal(signal.SIGTERM, quit)

    # create web server
    filepath = os.path.normpath(os.path.abspath(config.httpd_docs))
    httpd = MoinServer((config.httpd_host, config.httpd_port), filepath)

    # start it
    if sys.platform == 'win32':
        stdout = sys.stdout

        # run threaded server
        httpd.serve_in_thread()

        # main thread accepts signal
        i = 0
        while not httpd._abort:
            i = i + 1
            stdout.write("\|/-"[i%4] + "\r")
            time.sleep(1)
    else:
        # if run as root, change to configured user
        if os.getuid() == 0:
            if not config.httpd_user:
                print "Won't run as root, set the httpd_user config variable!"
                sys.exit(1)
            
            import pwd
            try:
                pwentry = pwd.getpwnam(config.httpd_user)
            except KeyError:
                print "Can't find httpd_user '%s'!" % (config.httpd_user,)
                sys.exit(1)

            uid = pwentry[2]
            os.setreuid(uid, uid)

        httpd.serve_forever()

if __name__ == "__main__":
    run()

