# -*- coding: utf-8 -*-
"""
    Mod Python WSGI Gateway
    =======================

    This module implements a mod_python wsgi gateway proving full compatibility
    with wsgi 1.0

    You have some possibilities for running such an application. Either using
    a handler module::

        from modpywsgi import WSGIServer
        from yourapplication import app

        srv = WSGIServer(app)
        def handler(req):
            return srv.run(req)

    of by using the internal one an activating it using an .htaccess::

        SetHandler python-program
        PythonHandler modpywsgi::handler
        PythonOption application yourapplication::app

    license: GNU GPL
"""
from __future__ import generators
from mod_python import apache

__author__ = 'Armin Ronacher <armin.ronacher@active-4.com>'


class WSGIServer(object):

    def __init__(self, application):
        self._application = application

    def run(self, req):
        environ = dict(apache.build_cgi_env(req))
        options = req.get_options()

        # we define those classes here to don't
        # give the user access to the mod python request
        # object using environ['wsgi.input']._req or
        # something similar.
        class InputStream(object):
            def close(self):
                pass
            def read(self, size=-1):
                return req.read(size)
            def readline(self):
                return req.readline()
            def readlines(self, hint=-1):
                return req.readlines(hint)
            def flush(self):
                pass
            def write(self, s):
                pass
            def writelines(self, seq):
                pass
            def __iter__(self):
                while True:
                    line = self.readline()
                    if not line:
                        return
                    yield line

        class ErrorStream(object):
            def read(self, size=-1):
                return ''
            def readline(self):
                return '\n'
            def readlines(self, hint=-1):
                return []
            def flush(self):
                pass
            def write(self, s):
                req.log_error(s)
            def writelines(self, seq):
                for item in seq:
                    req.log_error(item)
            def __iter__(self):
                return iter(int, 0)
        
        try:
            threaded = apache.mpm_query(apache.AP_MPMQ_IS_THREADED)
            forked = apache.mpm_query(apache.AP_MPMQ_IS_FORKED)
        except AttributeError:
            threaded = options.get('multithread', '').lower() == 'on'
            forked = options.get('multiprocess', '').lower() == 'on'
        
        if 'SCRIPT_NAME' in options:
            environ['SCRIPT_NAME'] = options['SCRIPT_NAME']
            path_info = req.uri[len(options['SCRIPT_NAME']):]
            if path_info:
                environ['PATH_INFO'] = path_info

        if environ.get('HTTPS', '').lower() in ('1', 'yes', 'on'):
            url_scheme = 'https'
        else:
            url_scheme = 'http'

        environ.update({
            'wsgi.input':           InputStream(),
            'wsgi.error':           ErrorStream(),
            'wsgi.version':         (1, 0),
            'wsgi.run_once':        False,
            'wsgi.url_scheme':      url_scheme,
            'wsgi.multithread':     threaded,
            'wsgi.multiprocess':    forked
        })

        req.content_type = 'text/plain'

        headers_set = []
        headers_sent = []

        def write(data):
            if not headers_set:
                raise AssertionError('write() before start_response()')
            elif not headers_sent:
                status, response_headers = headers_sent[:] = headers_set
                req.status = int(status[:3])
                for key, value in response_headers:
                    if key.lower() == 'content-length':
                        req.set_content_length(int(value))
                    elif key.lower() == 'content-type':
                        req.content_type = value
                    else:
                        req.headers_out.add(key, value)
            req.write(data)

        def start_response(status, response_headers, exc_info=None):
            if exc_info:
                try:
                    if headers_sent:
                        raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None
            elif headers_set:
                raise AssertionError('Headers already set!')
            headers_set[:] = [status, response_headers]
            return write

        result = self._application(environ, start_response)
        try:
            for data in result:
                if data:
                    write(data)
            if not headers_sent:
                write('')
        finally:
            if hasattr(result, 'close'):
                result.close()
            return apache.OK


def handler(req):
    """
    A mod_python compatible handler.
    Use it by putting this into your .htaccess::

        SetHandler python-program
        PythonHandler modpywsgi::handler
        PythonOption application yourmodule::YourApplication
    """
    options = req.get_options()
    modname, app = options['application'].split('::', 1)
    module = __import__(modname)
    app = getattr(module, app)
    srv = WSGIServer(app)
    return srv.run(req)
