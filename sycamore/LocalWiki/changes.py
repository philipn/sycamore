from LocalWiki import wikidb, wikiutil

class Edit(object):
    def __init__(self, pagename=None, time, editor=None, type=None, comment=None, remote_addr=None, proxy_addr=None):
        self.pagename = pagename
        self.time = time
        self.editor = editor
        self.type = type
        self.comment = comment
        self.remote_addr = remote_addr
        self.proxy_addr = proxy_addr


class Changes(object):
    query = ''

    def __init__(self, *args, **kwargs):
        if len(args) > 0:
            self.query = args[0] # the first one is our query
        else:
            self.query = self.makeQuery(**kwargs)

        self.conn = wikidb.connect()
        self.cursor = self.conn.cursor()
        self.cursor.execute(self.query)

    def makeQuery(self, **kwargs):
        pass

    def next(self):
        row = self.cursor.fetchone()
        if not row:
            raise StopIteration
        return Edit(*row)