"""
    LocalWiki event log class

    @license: GNU GPL, see COPYING for details.
"""

from logfile import LogFile
import LocalWiki.util.web
from LocalWiki import config, util
import os.path, urllib, time

class EventLog(LogFile):
    def __init__(self, filename=None, buffer_size=65536):
        if filename == None:
            filename = os.path.join(config.data_dir, 'event.log')
        LogFile.__init__(self, filename, buffer_size)

    def add(self, request, eventtype, values={}, add_http_info=1):
        """ Write an event of type `eventtype, with optional key/value
        pairs appended (i.e. you have to pass a dict).
        """
        if LocalWiki.util.web.isSpiderAgent():
            return
        
        kvlist = values.items()
        if add_http_info:
            for key in ['remote_addr', 'http_user_agent', 'http_referer']:
                val = request.__dict__.get(key, '')
                if val:
                    kvlist.append((key.upper(), val)) # HTTP stuff is UPPERCASE
        kvpairs = ""
        for key, val in kvlist:
            if kvpairs: kvpairs = kvpairs + "&"
            kvpairs = "%s%s=%s" % (kvpairs, urllib.quote(key), urllib.quote(val))
        self._add("%s\t%s\t%s\n" % (time.time(), eventtype, kvpairs))

    def noreq_add(self, request__dict, eventtype, values={}, add_http_info=1):
        """ Write an event of type `eventtype, with optional key/value
        pairs appended (i.e. you have to pass a dict).
        """
        if LocalWiki.util.web.isSpiderAgent():
            return

        kvlist = values.items()
        if add_http_info:
            for key in ['remote_addr', 'http_user_agent', 'http_referer']:
                val = request__dict__.get(key, '')
                if val:
                    kvlist.append((key.upper(), val)) # HTTP stuff is UPPERCASE
        kvpairs = ""
        for key, val in kvlist:
            if kvpairs: kvpairs = kvpairs + "&"
            kvpairs = "%s%s=%s" % (kvpairs, urllib.quote(key), urllib.quote(val))
        self._add("%s\t%s\t%s\n" % (time.time(), eventtype, kvpairs))

    def parser(self, line):
        try:
            time, eventtype, kvpairs = line.rstrip().split('\t')
        except ValueError:
            # badly formatted line in file, skip it
            return None
        return (float(time), eventtype, LocalWiki.util.web.parseQueryString(kvpairs))
                                                                        
    def set_filter(self, event_types = None):
        if event_types == None: self.filter = None
        else: self.filter = lambda line: (line[1] in event_types)
        
