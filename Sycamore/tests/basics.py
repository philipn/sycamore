import sys, os, unittest, random
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..'))])
import __init__

from Sycamore import request, config
_did_rollback = False

class RequestBasics(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName=methodName)
        self.request = request.RequestDummy()
        global _did_rollback
        _did_rollback = False

    def __del__(self):
        """Disconnect from the database and do not commit data."""
        global _did_rollback
        if not _did_rollback:
            self.request.do_commit = False
            self.request.db_disconnect()
            _did_rollback = True


class RequestBasicsTest(RequestBasics):
    knownEnvs = [
        ({'HTTP_REFERER': 'http://topsikiw.org/Wiki_Settings/CSS?sendfile=true&file=screen.css','SCRIPT_NAME': '', 'HTTP_IF_MODIFIED_SINCE': 'Thu, 01 Jan 1970 00:00:00 GMT', 'REQUEST_METHOD': 'GET', 'PATH_INFO': '/Wiki_Settings/Images', 'SERVER_PROTOCOL': 'HTTP/1.1', 'QUERY_STRING': 'sendfile=true&file=logo_background.png', 'CONTENT_LENGTH': '', 'HTTP_ACCEPT_CHARSET': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'HTTP_CONNECTION': 'keep-alive', 'HTTP_COOKIE': 'topsikiw_2Eorg_2CID="1148025122.31.7170,n7Ujcqw1ZqV1ajPtzedcRWH/YXE=,f1J/jJo8K+ZtyRQV+8YjIvGrxBE="; Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'SERVER_NAME': 'localhost', 'REMOTE_ADDR': '127.0.0.1', 'SERVER_PORT': '80', 'HTTP_HOST': 'topsikiw.org', 'HTTP_CACHE_CONTROL': 'max-age=0', 'HTTP_ACCEPT': 'image/png,*/*;q=0.5', 'HTTP_ACCEPT_LANGUAGE': 'en-us,en;q=0.5', 'CONTENT_TYPE': '', 'REMOTE_HOST': 'localhost', 'HTTP_ACCEPT_ENCODING': 'gzip,deflate', 'HTTP_KEEP_ALIVE': '300'}
        ,  
        {'http_user_agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'server_name': 'localhost', 'http_referer': 'http://topsikiw.org/Wiki_Settings/CSS?sendfile=true&file=screen.css', 'remote_addr': '127.0.0.1', 'is_ssl': False, 'http_accept_language': 'en-us,en;q=0.5', 'script_name': '', 'saved_cookie': 'topsikiw_2Eorg_2CID="1148025122.31.7170,n7Ujcqw1ZqV1ajPtzedcRWH/YXE=,f1J/jJo8K+ZtyRQV+8YjIvGrxBE="; Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'request_method': 'GET', 'http_host': 'topsikiw.org', 'path_info': '/Wiki_Settings/Images', 'server_port': '80', 'query_string': 'sendfile=true&file=logo_background.png', 'proxy_addr': None, 'auth_username': None, 'http_accept_encoding': 'gzip,deflate', 'do_gzip': True}
        ),
        (
        {'HTTP_REFERER': 'http://topsikiw.org/', 'SCRIPT_NAME': '', 'REQUEST_METHOD': 'GET', 'PATH_INFO': '/Front_Page', 'SERVER_PROTOCOL': 'HTTP/1.1', 'QUERY_STRING': 'action=userform&logout=Logout', 'CONTENT_LENGTH': '', 'HTTP_ACCEPT_CHARSET': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'HTTP_CONNECTION': 'keep-alive', 'HTTP_COOKIE': 'topsikiw_2Eorg_2CID="1148025122.31.7170,n7Ujcqw1ZqV1ajPtzedcRWH/YXE=,f1J/jJo8K+ZtyRQV+8YjIvGrxBE="; Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'SERVER_NAME': 'localhost', 'REMOTE_ADDR': '127.0.0.1', 'wsgi.url_scheme': 'http', 'SERVER_PORT': '80', 'HTTP_HOST': 'topsikiw.org', 'wsgi.multithread': True, 'HTTP_ACCEPT': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5', 'wsgi.version': (1, 0), 'wsgi.run_once': True, 'wsgi.multiprocess': False, 'HTTP_ACCEPT_LANGUAGE': 'en-us,en;q=0.5', 'CONTENT_TYPE': '', 'REMOTE_HOST': 'localhost', 'HTTP_ACCEPT_ENCODING': 'gzip,deflate', 'HTTP_KEEP_ALIVE': '300'}
        , 
        {'http_user_agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'server_name': 'localhost', 'http_referer': 'http://topsikiw.org/', 'remote_addr': '127.0.0.1', 'is_ssl': False, 'http_accept_language': 'en-us,en;q=0.5', 'script_name': '', 'saved_cookie': 'topsikiw_2Eorg_2CID="1148025122.31.7170,n7Ujcqw1ZqV1ajPtzedcRWH/YXE=,f1J/jJo8K+ZtyRQV+8YjIvGrxBE="; Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'request_method': 'GET', 'http_host': 'topsikiw.org', 'path_info': '/Front_Page', 'server_port': '80', 'query_string': 'action=userform&logout=Logout', 'proxy_addr': None, 'auth_username': None, 'http_accept_encoding': 'gzip,deflate', 'do_gzip': True}
        ),
        (
        {'HTTP_REFERER': 'http://topsikiw.org/Front_Page?action=edit', 'SCRIPT_NAME': '', 'REQUEST_METHOD': 'POST', 'PATH_INFO': '/Front_Page', 'SERVER_PROTOCOL': 'HTTP/1.1', 'QUERY_STRING': '', 'CONTENT_LENGTH': '120', 'HTTP_ACCEPT_CHARSET': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'HTTP_CONNECTION': 'keep-alive', 'HTTP_COOKIE': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'SERVER_NAME': 'localhost', 'REMOTE_ADDR': '127.0.0.1', 'wsgi.url_scheme': 'http', 'SERVER_PORT': '80', 'HTTP_HOST': 'topsikiw.org', 'wsgi.multithread': True, 'HTTP_ACCEPT': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5', 'wsgi.version': (1, 0), 'wsgi.run_once': True, 'wsgi.multiprocess': False, 'HTTP_ACCEPT_LANGUAGE': 'en-us,en;q=0.5', 'CONTENT_TYPE': 'application/x-www-form-urlencoded', 'REMOTE_HOST': 'localhost', 'HTTP_ACCEPT_ENCODING': 'gzip,deflate', 'HTTP_KEEP_ALIVE': '300'}
        ,
        {'http_user_agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'server_name': 'localhost', 'http_referer': 'http://topsikiw.org/Front_Page?action=edit', 'remote_addr': '127.0.0.1', 'is_ssl': False, 'http_accept_language': 'en-us,en;q=0.5', 'script_name': '', 'saved_cookie': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'request_method': 'POST', 'http_host': 'topsikiw.org', 'path_info': '/Front_Page', 'server_port': '80', 'query_string': '', 'proxy_addr': None, 'auth_username': None, 'http_accept_encoding': 'gzip,deflate', 'do_gzip': True}
        )
        ,
        (
        {'HTTP_REFERER': 'http://topsikiw.org/People?action=edit', 'SCRIPT_NAME': '', 'REQUEST_METHOD': 'POST', 'PATH_INFO': '/People', 'SERVER_PROTOCOL': 'HTTP/1.1', 'QUERY_STRING': '', 'CONTENT_LENGTH': '198', 'HTTP_ACCEPT_CHARSET': 'utf-8, utf-8;q=0.5, *;q=0.5', 'HTTP_USER_AGENT': 'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)', 'HTTP_CONNECTION': 'Keep-Alive', 'SERVER_NAME': 'localhost', 'REMOTE_ADDR': '127.0.0.1', 'wsgi.url_scheme': 'http', 'SERVER_PORT': '80', 'HTTP_PRAGMA': 'no-cache', 'HTTP_HOST': 'topsikiw.org', 'wsgi.multithread': True, 'HTTP_CACHE_CONTROL': 'no-cache', 'HTTP_ACCEPT': 'text/html, image/jpeg, image/png, text/*, image/*, */*', 'wsgi.version': (1, 0), 'wsgi.run_once': True, 'wsgi.multiprocess': False, 'HTTP_ACCEPT_LANGUAGE': 'en', 'CONTENT_TYPE': 'application/x-www-form-urlencoded', 'REMOTE_HOST': 'localhost', 'HTTP_ACCEPT_ENCODING': 'x-gzip, x-deflate, gzip, deflate'}
        ,
        {'http_user_agent': 'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)', 'server_name': 'localhost', 'http_referer': 'http://topsikiw.org/People?action=edit', 'remote_addr': '127.0.0.1', 'is_ssl': False, 'http_accept_language': 'en', 'script_name': '', 'saved_cookie': '', 'request_method': 'POST', 'http_host': 'topsikiw.org', 'path_info': '/People', 'server_port': '80', 'query_string': '', 'proxy_addr': None, 'auth_username': None, 'http_accept_encoding': 'x-gzip, x-deflate, gzip, deflate', 'do_gzip': False}
        ),
        ]

    knownEnvXForward = [
        (
        {'HTTP_X_FORWARDED_FOR': 'not an ip address', 'REMOTE_ADDR': '17.222.68.2', 'HTTP_REFERER': 'http://topsikiw.org/Front_Page?action=edit', 'SCRIPT_NAME': '', 'REQUEST_METHOD': 'POST', 'PATH_INFO': '/Front_Page', 'SERVER_PROTOCOL': 'HTTP/1.1', 'QUERY_STRING': '', 'CONTENT_LENGTH': '120', 'HTTP_ACCEPT_CHARSET': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'HTTP_CONNECTION': 'keep-alive', 'HTTP_COOKIE': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'SERVER_NAME': 'localhost', 'wsgi.url_scheme': 'http', 'SERVER_PORT': '80', 'HTTP_HOST': 'topsikiw.org', 'wsgi.multithread': True, 'HTTP_ACCEPT': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5', 'wsgi.version': (1, 0), 'wsgi.run_once': True, 'wsgi.multiprocess': False, 'HTTP_ACCEPT_LANGUAGE': 'en-us,en;q=0.5', 'CONTENT_TYPE': 'application/x-www-form-urlencoded', 'REMOTE_HOST': 'localhost', 'HTTP_ACCEPT_ENCODING': 'gzip,deflate', 'HTTP_KEEP_ALIVE': '300'}
        ,
        {'http_user_agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'server_name': 'localhost', 'http_referer': 'http://topsikiw.org/Front_Page?action=edit', 'remote_addr': '17.222.68.2', 'is_ssl': False, 'http_accept_language': 'en-us,en;q=0.5', 'script_name': '', 'saved_cookie': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'request_method': 'POST', 'http_host': 'topsikiw.org', 'path_info': '/Front_Page', 'server_port': '80', 'query_string': '', 'proxy_addr': None, 'auth_username': None, 'http_accept_encoding': 'gzip,deflate', 'do_gzip': True}
        )
        ,
        (
        {'HTTP_X_FORWARDED_FOR': '192.168.1.2', 'REMOTE_ADDR': '17.222.68.2', 'HTTP_REFERER': 'http://topsikiw.org/Front_Page?action=edit', 'SCRIPT_NAME': '', 'REQUEST_METHOD': 'POST', 'PATH_INFO': '/Front_Page', 'SERVER_PROTOCOL': 'HTTP/1.1', 'QUERY_STRING': '', 'CONTENT_LENGTH': '120', 'HTTP_ACCEPT_CHARSET': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'HTTP_CONNECTION': 'keep-alive', 'HTTP_COOKIE': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'SERVER_NAME': 'localhost', 'wsgi.url_scheme': 'http', 'SERVER_PORT': '80', 'HTTP_HOST': 'topsikiw.org', 'wsgi.multithread': True, 'HTTP_ACCEPT': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5', 'wsgi.version': (1, 0), 'wsgi.run_once': True, 'wsgi.multiprocess': False, 'HTTP_ACCEPT_LANGUAGE': 'en-us,en;q=0.5', 'CONTENT_TYPE': 'application/x-www-form-urlencoded', 'REMOTE_HOST': 'localhost', 'HTTP_ACCEPT_ENCODING': 'gzip,deflate', 'HTTP_KEEP_ALIVE': '300'}
        ,
        {'http_user_agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'server_name': 'localhost', 'http_referer': 'http://topsikiw.org/Front_Page?action=edit', 'remote_addr': '192.168.1.2', 'is_ssl': False, 'http_accept_language': 'en-us,en;q=0.5', 'script_name': '', 'saved_cookie': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'request_method': 'POST', 'http_host': 'topsikiw.org', 'path_info': '/Front_Page', 'server_port': '80', 'query_string': '', 'proxy_addr': '17.222.68.2', 'auth_username': None, 'http_accept_encoding': 'gzip,deflate', 'do_gzip': True}
        )

        ]

    knownEnvXForwardOff = [
        (
        {'HTTP_X_FORWARDED_FOR': 'not an ip address', 'REMOTE_ADDR': '17.222.68.2', 'HTTP_REFERER': 'http://topsikiw.org/Front_Page?action=edit', 'SCRIPT_NAME': '', 'REQUEST_METHOD': 'POST', 'PATH_INFO': '/Front_Page', 'SERVER_PROTOCOL': 'HTTP/1.1', 'QUERY_STRING': '', 'CONTENT_LENGTH': '120', 'HTTP_ACCEPT_CHARSET': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'HTTP_CONNECTION': 'keep-alive', 'HTTP_COOKIE': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'SERVER_NAME': 'localhost', 'wsgi.url_scheme': 'http', 'SERVER_PORT': '80', 'HTTP_HOST': 'topsikiw.org', 'wsgi.multithread': True, 'HTTP_ACCEPT': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5', 'wsgi.version': (1, 0), 'wsgi.run_once': True, 'wsgi.multiprocess': False, 'HTTP_ACCEPT_LANGUAGE': 'en-us,en;q=0.5', 'CONTENT_TYPE': 'application/x-www-form-urlencoded', 'REMOTE_HOST': 'localhost', 'HTTP_ACCEPT_ENCODING': 'gzip,deflate', 'HTTP_KEEP_ALIVE': '300'}
        ,
        {'http_user_agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'server_name': 'localhost', 'http_referer': 'http://topsikiw.org/Front_Page?action=edit', 'remote_addr': '17.222.68.2', 'is_ssl': False, 'http_accept_language': 'en-us,en;q=0.5', 'script_name': '', 'saved_cookie': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'request_method': 'POST', 'http_host': 'topsikiw.org', 'path_info': '/Front_Page', 'server_port': '80', 'query_string': '', 'proxy_addr': None, 'auth_username': None, 'http_accept_encoding': 'gzip,deflate', 'do_gzip': True}
        )
        ,
        (
        {'HTTP_X_FORWARDED_FOR': '192.168.1.2', 'REMOTE_ADDR': '17.222.68.2', 'HTTP_REFERER': 'http://topsikiw.org/Front_Page?action=edit', 'SCRIPT_NAME': '', 'REQUEST_METHOD': 'POST', 'PATH_INFO': '/Front_Page', 'SERVER_PROTOCOL': 'HTTP/1.1', 'QUERY_STRING': '', 'CONTENT_LENGTH': '120', 'HTTP_ACCEPT_CHARSET': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'HTTP_CONNECTION': 'keep-alive', 'HTTP_COOKIE': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'SERVER_NAME': 'localhost', 'wsgi.url_scheme': 'http', 'SERVER_PORT': '80', 'HTTP_HOST': 'topsikiw.org', 'wsgi.multithread': True, 'HTTP_ACCEPT': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5', 'wsgi.version': (1, 0), 'wsgi.run_once': True, 'wsgi.multiprocess': False, 'HTTP_ACCEPT_LANGUAGE': 'en-us,en;q=0.5', 'CONTENT_TYPE': 'application/x-www-form-urlencoded', 'REMOTE_HOST': 'localhost', 'HTTP_ACCEPT_ENCODING': 'gzip,deflate', 'HTTP_KEEP_ALIVE': '300'}
        ,
        {'http_user_agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0 (Ubuntu-edgy)', 'server_name': 'localhost', 'http_referer': 'http://topsikiw.org/Front_Page?action=edit', 'remote_addr': '17.222.68.2', 'is_ssl': False, 'http_accept_language': 'en-us,en;q=0.5', 'script_name': '', 'saved_cookie': 'Davis_20WikiID="1088084990.24.48504,N4Lyy6h0YG20Y/uUnUauTJ35cEM=,zBLLyOqEtTUsotSQqraFwhqxauM="', 'request_method': 'POST', 'http_host': 'topsikiw.org', 'path_info': '/Front_Page', 'server_port': '80', 'query_string': '', 'proxy_addr': None, 'auth_username': None, 'http_accept_encoding': 'gzip,deflate', 'do_gzip': True}
        )

        ]

    wiki_farm_base_domains = ['localhost', 'wikispot.org', 'topsikiw.org', 'dwiki.org', 'example.com', 'example.org', 'wiki.example.org', 'wiki.example.com', 'wiki.example.com', 'wikispot.org', 'dwiki.org', 'wiki.lolpants.bbc.co.uk']

    wiki_farm_path_infos = [('/wikis/wikiname', 'wikiname'), ('/wikis/fuckingshit', 'fuckingshit'), ('/wikis/pants%20a%20lot', 'pants%20a%20lot'), ('/wikis/hi', 'hi'), ('/wikis/davis/Front_Page', 'davis'), ('/wikis/rochester/Wanted_Pages?action=edit', 'rochester')]

    wiki_farm_subdomains = [('www.test', 'test'), ('test', 'test'), ('hithere', 'hithere'), ('www.hithere', 'hithere'), ('this.is.a.test.pants', 'pants')]


    def __del__(self):
        """Disconnect from the database and do not commit data."""
        global _did_rollback
        if not _did_rollback:
            self.request.do_commit = False
            self.request.db_disconnect()
            _did_rollback = True

    def testSetupEnvArgs(self):
        """Request object should get proper attributes from the environment"""
        for value in self.knownEnvs:
            env, expected = value
            self.request.setup_args(env=env)
            for attr, known_value in expected.iteritems():
                self.assertEqual(getattr(self.request, attr), known_value)

        for value in self.knownEnvXForward:
            config.trust_x_forwarded_for = True
            env, expected = value
            self.request.setup_args(env=env)
            for attr, known_value in expected.iteritems():
                self.assertEqual(getattr(self.request, attr), known_value)

        for value in self.knownEnvXForwardOff:
            config.trust_x_forwarded_for = False
            env, expected = value
            self.request.setup_args(env=env)
            for attr, known_value in expected.iteritems():
                self.assertEqual(getattr(self.request, attr), known_value)

    def testWikiFarmSetup(self):
        """Request should use environment path to find wiki's name."""
        config.wiki_farm = False
        self.assertEqual(request.setup_wiki_farm(self.request), None)

        config.wiki_farm = True

        for domain in self.wiki_farm_base_domains:
            config.wiki_farm_subdomains = False
            config.wiki_base_domain = domain

            config.wiki_farm_dir = 'wikis'
            for path, correct_wiki_name in self.wiki_farm_path_infos:
                self.request.env = self.knownEnvs[random.randint(0, len(self.knownEnvs)-1)][0]
                self.request.env['PATH_INFO'] = path
                wiki_name = request.setup_wiki_farm(self.request)
                self.assertEqual(wiki_name, correct_wiki_name)
            
            config.wiki_farm_subdomains = True
            for subdomain, correct_wiki_name in self.wiki_farm_subdomains:
                self.request.env = self.knownEnvs[random.randint(0, len(self.knownEnvs)-1)][0]
                self.request.env['HTTP_HOST'] = subdomain + '.' + domain
                wiki_name = request.setup_wiki_farm(self.request)
                self.assertEqual(wiki_name, correct_wiki_name)

    def testRelativeDir(self):
        """Sets relative dir properly"""
        config.relative_dir = ''
        self.assertEqual('', request.getRelativeDir(self.request))
        config.relative_dir = 'wiki/index.cgi'
        self.assertEqual('wiki/index.cgi', request.getRelativeDir(self.request))
        config.relative_dir = 'index.cgi'
        self.assertEqual('index.cgi', request.getRelativeDir(self.request))
        config.relative_dir = 'index.cgi'
        self.assertEqual('index.cgi', request.getRelativeDir(self.request))
        config.relative_dir = '/index.cgi'
        self.assertEqual('/index.cgi', request.getRelativeDir(self.request))
        config.relative_dir = '/bad/index.cgi'
        self.assertEqual('/bad/index.cgi', request.getRelativeDir(self.request))


if __name__ == "__main__":
    unittest.main()
