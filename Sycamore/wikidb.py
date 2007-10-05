# -*- coding: utf-8 -*-
"""
    Sycamore - Wiki database support functions

    @copyright: 2005-2007 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""
# User calls wikidb.connect() to get a WikiDB object.
# We only connect to the database when we execute a query.
# (But it's all invisible to you.)

# Imports
import time
import array
import copy

from Sycamore import config
from Sycamore.support import pool

if config.db_type == 'mysql':
    dbapi_module = __import__("MySQLdb")
elif config.db_type == 'postgres':
    dbapi_module = __import__("psycopg2")

pool_size = config.db_pool_size
max_overflow = config.db_max_overflow

Binary = dbapi_module.Binary
if config.db_pool:
    dbapi = pool.manage(dbapi_module, pool_size=pool_size,
                        max_overflow=max_overflow)
else:
    dbapi = dbapi_module
dbapi.Binary = Binary

MAX_CONNECTION_ATTEMPTS = pool_size + 10
RC_MAX_DAYS = 7

# MySQL error numbers for 'lost connection' errors
CONNECTION_ERRORS = [2006, 2013]

# the max number of changes we ever display on RC
ABSOLUTE_RC_CHANGES_LIMIT = 1000

def fixUpStrings(item):
    def doFixUp(i):
        if config.db_type != 'mysql' and type(i) == str:
            return i.decode(config.db_charset)
        elif type(i) == tuple:
            return fixUpStrings(i)
        return i

    if type(item) == tuple or type(item) == list:
        return [doFixUp(i) for i in item]
    return doFixUp(item)


class WikiDB(object):
    def __init__(self, db):
        self.db = db
        self.do_commit = False

    def close(self):
        if self.db and (not config.db_pool or self.db.alive):
            self.db.close()
            del self.db # ESSENTIAL
            # the del here is needed so the connection pool gets
            # the element back
    
    def cursor(self):
        return WikiDBCursor(self)
    
    def commit(self):
        self.db.commit()

    def rollback(self):
        if self.db and (not config.db_pool or self.db.alive):
            self.db.rollback()


def _test_connection(db):
    """
    Tries to issue a test query.
    If it fails because the connection is dead or because the
    database went away then we try to fix this.
    """
    def _try_execute(db):
        test_query = "SELECT 1"
        had_error = False
        try:
            db.db_cursor = db.db.cursor()
            db.db_cursor.execute(test_query)
            db.db_cursor.fetchone()
        except:
             had_error = True

        return had_error

    had_error = _try_execute(db)
    
    i = 0
    cant_connect = False
    while had_error and i < MAX_CONNECTION_ATTEMPTS:
        i += 1
        if config.db_pool:
            db.db.alive = False # mark as dead
        del db.db
        db.db_cursor = None
        # keep trying to get a good connection from the pool
        try:
            db.db = real_connect()
        except:
            had_error = True
            cant_connect = True
            break

        had_error = _try_execute(db)

    if had_error and (cant_connect or i == MAX_CONNECTION_ATTEMPTS):
        raise db.ConnectionError, "Could not connect to database."


class WikiDBCursor(object):
    def __init__(self, db):
        self.db = db
        if db.db:
            self.db_cursor = db.db.cursor()
        else:
            self.db_cursor = None

    class ConnectionError(Exception):
        pass

    def execute(self, query, args={}, isWrite=False):
        if isWrite:
            self.db.do_commit = True
        if args:
            args = _fixArgs(args)

        if not self.db.db:
            # connect to the db for real for the first time 
            self.db.db = real_connect()
            _test_connection(self)
            self.db_cursor.execute(query, args) 
        else:
            self.db_cursor.execute(query, args) 

    def executemany(self, query, args_seq=(), isWrite=False):
        if isWrite:
            self.db.do_commit = True
        if args_seq:
            args_seq = [_fixArgs(arg) for arg in args_seq]

        if not self.db.db:
            # connect to the db for real for the first time 
            self.db.db = real_connect()
            _test_connection(self)
            self.db_cursor.executemany(query, args_seq) 
        else: 
            self.db_cursor.executemany(query, args_seq) 

    def fetchone(self):
        return fixUpStrings(self.db_cursor.fetchone())

    def fetchall(self):
        return fixUpStrings(self.db_cursor.fetchall())

    def close(self):
        if self.db_cursor:
            self.db_cursor.close()
            del self.db_cursor
            del self.db

def _fixArgs(args):
    """
    Converts python floats to limited-precision float strings before sending
    them to the db.  This is so that we can keep the precision consistent
    between implementations.
    
    (I am not sure of a more elegant way to do this without using a
     specialized mysql type. This at least keeps consistency and keeps the
     accidential programmer from being throw off by weird
     floating point issues)
    
    The idea is that we limit the length of our floats to be
    five places after the decimal point.
    Python's floats are bigger than this, and so are mysql's. So we know that
    our internal rounding will work and be consistent between the two.
    """

    def fixValue(o):
        if type(o) == float:
            return _floatToString(o)
        else:
            return o
    
    new_args = {}
    for k, v in args.iteritems():
        new_args[k] = fixValue(v) 
        
    return new_args

def _floatToString(f):
    """
    Converts a float to the proper length of double that mysql uses.
    We need to use this when we render a link (GET/POST) that displays a
    double from the db, because python's floats are bigger than mysql's floats.
    """
    return "%.5f" % f

def binaryToString(b):
    """
    Converts a binary format (as returned by the db) to a string.
    Different modules do this differently :-/
    """
    if config.db_type == 'postgres':
        return str(b)
    elif config.db_type == 'mysql':
        if not hasattr(b, 'tostring'):
            return b
        return b.tostring()

def connect():
    """
    A 'pretend' connect.

    We don't really connect to the db until we internally call real_connect().
    We do this when we see our first query.
    """
    return WikiDB(None)

def real_connect():
    """
    Actually initiate a connection to the database.
    """
    d = {}
    global dbapi
    if config.db_host:
        d['host'] = config.db_host
    if config.db_user:
        d['user'] = config.db_user
    if config.db_name:
        if config.db_type == 'mysql':
            d['db'] = config.db_name
        elif config.db_type == 'postgres':
            d['database'] = config.db_name
    if config.db_user_password:
        if config.db_type == 'postgres':
            d['password'] = config.db_user_password
        elif config.db_type == 'mysql':
            d['passwd'] = config.db_user_password
    if config.db_socket:
        d['unix_socket'] = config.db_socket
    if config.db_type == 'mysql':
        d['init_command'] = 'SET NAMES utf8'
        d['charset'] = 'utf8'
    
    db = dbapi.connect(**d)
    if config.db_type == 'mysql':
        had_error = False
        try:
            db.ping()
        except dbapi_module.OperationalError, (errno, strerror):
            if errno in CONNECTION_ERRORS:
                had_error = True
                while had_error:
                    if config.db_pool:
                        db.alive = False
                    del db
                    db = dbapi.connect(**d)
                    # keep trying to get a good connection from the pool
                    try:
                        db.ping()
                    except dbapi_module.OperationalError, (errno, strerror):
                        if errno in CONNECTION_ERRORS:
                            had_error = True
                        else:
                            had_error = False
                    else:
                        had_error = False
            else:
                raise dbapi_module.OperationalError, (errno, strerror)
    return db

def getFile(request, dict, deleted=False, thumbnail=False, version=0,
            ticket=None, size=None, fresh=False):
    """
    Get the file from the database.

    @param dict: a dictionary with possible keys:
                     filename, page_name, and file_version.
    @param deleted: whether or not the version of the file we want is a
                    deleted version.
    @param thumbnail: whether or not the file is an image thumbnail.
    @param version: he unix timestamp of the version of the file we want.
                    Leave blank for the current version.
    @param ticket: request ticket that we need to avoid
                   thumbnail regeneration.  Only applies for thumbnails.
    @param size: the integer size of the image we are grabbing.
                 Only applies for images.
    @param fresh: if True then grab only fresh data -- nothing stale
                  from the cache.
    @return: either False if the file doesn't exist, or a tuple:
            (filecontentstring, last_modified_date)
    """
    def assemble_query():
        from Sycamore.wikiutil import mc_quote
        # let's assemble the query and key if we use memcache
        key = None
        query = ''
        if not deleted and not thumbnail and not version:
            if config.memcache:
                key = "files:%s,%s" % (mc_quote(dict['filename']),
                                       mc_quote(dict['page_name']))
            query = """SELECT file, uploaded_time from files
                       where name=%(filename)s and
                             attached_to_pagename=%(page_name)s and
                             wiki_id=%(wiki_id)s"""
        elif thumbnail:
            if not ticket:
                if config.memcache:
                  key = "thumbnails:%s,%s" % (mc_quote(dict['filename']),
                                              mc_quote(dict['page_name']))
                query = """SELECT image, last_modified from thumbnails
                           where name=%(filename)s and
                                 attached_to_pagename=%(page_name)s and
                                 wiki_id=%(wiki_id)s"""
            else: 
                if config.memcache:
                    size_encoded, ticket_encoded = size, ticket
                    if size:
                        size_encoded = size.encode(config.charset)
                    if ticket:
                        ticket_encoded = ticket.encode(config.charset)
                    key = "thumbnails:%s,%s" % (mc_quote(dict['filename']),
                                                size_encoded or ticket_encoded)
        elif deleted:
            # default behavior is to grab the latest backup
            # version of the image
            if not version:
                if config.memcache:
                    key = "oldfiles:%s,%s" % (mc_quote(dict['filename']),
                                              mc_quote(dict['page_name']))
                query = """SELECT file, uploaded_time from oldFiles
                           where name=%(filename)s and
                                 attached_to_pagename=%(page_name)s and
                                 wiki_id=%(wiki_id)s
                           order by uploaded_time desc;"""
            elif version:
                if config.memcache:
                    key = "oldfiles:%s,%s,%s" % (mc_quote(dict['filename']),
                                                 mc_quote(dict['page_name']),
                                                 version)
                query = """SELECT file, uploaded_time from oldFiles
                           where name=%(filename)s and
                                 attached_to_pagename=%(page_name)s and
                                 uploaded_time=%(file_version)s and
                                 wiki_id=%(wiki_id)s"""

        return query, key

    file_obj = None
    dict['page_name'] = dict['page_name'].lower()
    dict['wiki_id'] = request.config.wiki_id

    query, key = assemble_query()

    if config.memcache and key and not fresh:
        file_obj = request.mc.get(key)

    if file_obj is None:
        from wikiutil import isImage
        if ticket and isImage(dict['filename']):
           # we generate the thumbnail..weee
           from Sycamore.macro import image
           file_obj = (image.generateThumbnail(request, dict['page_name'],
                                               dict['filename'],
                                               dict['maxsize'],
                                               return_image=True),
                       0)
        else:
           request.cursor.execute(query, dict)
           file_obj = request.cursor.fetchone()
           if not file_obj:
                # False so that we know it's not there when we check the mc
                file_obj = False  
           else:
                # Messy because of a bug in python for pickling
                # array.array -- must convert to str before putting in memcache
                new_file_obj = (binaryToString(file_obj[0]), file_obj[1])
                file_obj = new_file_obj
           
        if config.memcache:
            request.mc.add(key, file_obj)

    if file_obj:
        return file_obj[0], float(file_obj[1])

def putFile(request, dict, thumbnail=False, do_delete=False, temporary=False,
            ticket=None, permanent=False):
    """
    Puts the file (found in dict) into the database.
    dict is a dictionary with possible keys: filename, filecontent,
                                             uploaded_time, uploaded_by,
                                             pagename, uploaded_by_ip,
                                             xsize, ysize, deleted_time,
                                             deleted_by, deleted_by_ip.
    """
    from Sycamore.wikiutil import mc_quote, isImage
    from Sycamore.Page import Page
    from Sycamore import caching
    from Sycamore.action.Files import get_filedict

    def set_cache_for_file():
        """
        Sets the memory cache for the new file.
        """
        if not config.memcache:
            return

        if not do_delete:
            if not thumbnail:
                table = 'files'
            else:
                table = 'thumbnails'
            if not temporary:
                key = "%s:%s,%s" % (table, mc_quote(dict['filename']),
                                    mc_quote(dict['pagename'].lower()))
            else:
                key = "%s,%s,%s" % (table, mc_quote(dict['filename']), ticket)
            image_obj = (raw_image, uploaded_time)
            request.mc.set(key, image_obj)
        else:
            if not thumbnail:
                key = "files:%s,%s" % (mc_quote(dict['filename']),
                                       mc_quote(dict['pagename'].lower()))
                request.mc.set(key, False)
            if is_image and thumbnail:
                key = "thumbnails:%s,%s" % (mc_quote(dict['filename']),
                                            mc_quote(dict['pagename'].lower()))
                request.mc.set(key, False)

        # set new file dict
        if not replaced_image:
            get_filedict(request, dict['pagename'], fresh=True, set=True)

    def rebuild_page_cache():
        """
        Rebuilds the page cache.
        """
        if not request.generating_cache and not request.previewing_page:
            from Sycamore import caching
            from Sycamore.Page import Page
            page = Page(dict['pagename'], request)
            if page.exists():
                page.buildCache()

    def handle_file_add():
        request.cursor.execute(
            """SELECT name from files
               where name=%(filename)s and
                     attached_to_pagename=%(pagename)s and
                     wiki_id=%(wiki_id)s""", dict)
        exists = request.cursor.fetchone()
        if exists:
            # backup file, then remove it  
            replaced_image = True
            request.cursor.execute(
                """INSERT into oldFiles
                       (name, file, uploaded_time, uploaded_by,
                        attached_to_pagename, deleted_time, deleted_by,
                        uploaded_by_ip, deleted_by_ip,
                        attached_to_pagename_propercased, wiki_id)
                   values
                       (%(filename)s,
                        (select file from files where name=%(filename)s and
                            attached_to_pagename=%(pagename)s and
                            wiki_id=%(wiki_id)s
                        ),
                        (select uploaded_time from files where
                            name=%(filename)s and
                            attached_to_pagename=%(pagename)s and
                            wiki_id=%(wiki_id)s
                        ),
                        (select uploaded_by from files where
                            name=%(filename)s and
                            attached_to_pagename=%(pagename)s and
                            wiki_id=%(wiki_id)s
                        ),
                        %(pagename)s, %(uploaded_time)s, %(uploaded_by)s,
                        (select uploaded_by_ip from files where
                            name=%(filename)s and
                            attached_to_pagename=%(pagename)s and
                            wiki_id=%(wiki_id)s
                        ),
                        %(uploaded_by_ip)s, %(pagename_propercased)s,
                        %(wiki_id)s)""", dict, isWrite=True)
            if is_image:
                request.cursor.execute(
                    """INSERT into oldImageInfo
                           (name, attached_to_pagename, xsize, ysize,
                            uploaded_time, wiki_id)
                       values
                           (%(filename)s, %(pagename)s,
                            (select xsize from imageInfo where
                                name=%(filename)s and
                                attached_to_pagename=%(pagename)s and
                                wiki_id=%(wiki_id)s
                            ),
                            (select ysize from imageInfo where
                                name=%(filename)s and
                                attached_to_pagename=%(pagename)s and
                                wiki_id=%(wiki_id)s
                            ),
                            (select uploaded_time from files where
                                name=%(filename)s and
                                attached_to_pagename=%(pagename)s and
                                wiki_id=%(wiki_id)s
                            ),
                            %(wiki_id)s)""", dict, isWrite=True)
                request.cursor.execute(
                    """DELETE from imageInfo
                       where name=%(filename)s and
                             attached_to_pagename=%(pagename)s and
                             wiki_id=%(wiki_id)s""", dict, isWrite=True)

            request.cursor.execute(
                """DELETE from files
                   where name=%(filename)s and
                         attached_to_pagename=%(pagename)s and
                         wiki_id=%(wiki_id)s""", dict, isWrite=True)

        request.cursor.execute(
            """INSERT into files
                   (name, file, uploaded_time, uploaded_by,
                    attached_to_pagename, uploaded_by_ip,
                    attached_to_pagename_propercased, wiki_id)
               values
                   (%(filename)s, %(filecontent)s, %(uploaded_time)s,
                    %(uploaded_by)s, %(pagename)s, %(uploaded_by_ip)s,
                    %(pagename_propercased)s, %(wiki_id)s)""",
            dict, isWrite=True)
        if is_image:
            request.cursor.execute(
                """INSERT into imageInfo
                       (name, attached_to_pagename, xsize, ysize, wiki_id)
                   values
                       (%(filename)s, %(pagename)s, %(xsize)s, %(ysize)s,
                        %(wiki_id)s)""", dict, isWrite=True)
      
        caching.updateRecentChanges(page)

    def handle_thumbnail_add():
        request.cursor.execute(
            """SELECT name from thumbnails
               where name=%(filename)s and
                     attached_to_pagename=%(pagename)s and
                     wiki_id=%(wiki_id)s""", dict)
        exists = request.cursor.fetchone()
        if exists:
            request.cursor.execute(
                """UPDATE thumbnails set
                       xsize=%(x)s, ysize=%(y)s, image=%(filecontent)s,
                       last_modified=%(uploaded_time)s
                   where name=%(filename)s and
                         attached_to_pagename=%(pagename)s and
                         wiki_id=%(wiki_id)s""", dict, isWrite=True)
        else:
            request.cursor.execute(
                """INSERT into thumbnails
                       (xsize, ysize, name, image, last_modified,
                        attached_to_pagename, wiki_id)
                   values
                       (%(x)s, %(y)s, %(filename)s, %(filecontent)s,
                        %(uploaded_time)s, %(pagename)s, %(wiki_id)s)""",
                dict, isWrite=True)

    def handle_file_delete():
        request.cursor.execute(
            """SELECT name from files
               where name=%(filename)s and
                     attached_to_pagename=%(pagename)s and
                     wiki_id=%(wiki_id)s""", dict)
        has_file = request.cursor.fetchone()
        if has_file:
            if not permanent:
                # backup file
                request.cursor.execute("""
                    INSERT into oldFiles
                        (name, attached_to_pagename, file, uploaded_by,
                         uploaded_time, deleted_time, deleted_by,
                         uploaded_by_ip, deleted_by_ip,
                         attached_to_pagename_propercased, wiki_id)
                    values
                        (%(filename)s, %(pagename)s,
                         (select file from files
                              where name=%(filename)s and
                                    attached_to_pagename=%(pagename)s and
                                    wiki_id=%(wiki_id)s
                         ),
                         (select uploaded_by from files
                              where name=%(filename)s and
                                    attached_to_pagename=%(pagename)s and
                                    wiki_id=%(wiki_id)s
                         ),
                         (select uploaded_time from files
                              where name=%(filename)s and
                                    attached_to_pagename=%(pagename)s and
                                    wiki_id=%(wiki_id)s
                         ),
                         %(deleted_time)s, %(deleted_by)s,
                         (select uploaded_by_ip from files
                              where name=%(filename)s and
                                    attached_to_pagename=%(pagename)s and
                                    wiki_id=%(wiki_id)s
                         ),
                         %(deleted_by_ip)s,
                         (select attached_to_pagename_propercased from files
                              where name=%(filename)s and
                                    attached_to_pagename=%(pagename)s and
                                    wiki_id=%(wiki_id)s
                         ),
                         %(wiki_id)s)""", dict, isWrite=True)
            else:
                # nuke all old cached versions of the file
                caching.deleteAllFileInfo(dict['filename'], dict['pagename'],
                                          request)
                # nuke all old versions
                request.cursor.execute(
                    """DELETE from oldFiles
                           where name=%(filename)s and
                                 attached_to_pagename=%(pagename)s and
                                 wiki_id=%(wiki_id)s""", dict, isWrite=True)

            if is_image:
                if not permanent:
                    # backup image info
                    request.cursor.execute(
                        """INSERT into oldImageInfo
                           (name, attached_to_pagename, xsize, ysize,
                            uploaded_time, wiki_id)
                           values
                           (%(filename)s, %(pagename)s,
                            (select xsize from imageInfo
                                 where name=%(filename)s and
                                       attached_to_pagename=%(pagename)s and
                                       wiki_id=%(wiki_id)s
                            ),
                            (select ysize from imageInfo
                                 where name=%(filename)s and
                                       attached_to_pagename=%(pagename)s and
                                       wiki_id=%(wiki_id)s
                            ),
                            (select uploaded_time from files
                                  where name=%(filename)s and
                                        attached_to_pagename=%(pagename)s and
                                        wiki_id=%(wiki_id)s
                            ),
                            %(wiki_id)s)""", dict, isWrite=True)
                
                else:
                    # nuke all old versions
                    request.cursor.execute(
                        """DELETE from oldImageInfo
                           where name=%(filename)s and
                                 attached_to_pagename=%(pagename)s and
                                 wiki_id=%(wiki_id)s""", dict, isWrite=True)
                # delete image info
                request.cursor.execute(
                    """DELETE from imageInfo
                       where name=%(filename)s and
                             attached_to_pagename=%(pagename)s and
                             wiki_id=%(wiki_id)s""", dict, isWrite=True)
            # delete file 
            request.cursor.execute(
                """DELETE from files
                   where name=%(filename)s and
                         attached_to_pagename=%(pagename)s and
                         wiki_id=%(wiki_id)s""", dict, isWrite=True)

            caching.updateRecentChanges(page)

    def handle_thumbnail_delete():
        """
        delete thumbnail.
        """
        request.cursor.execute(
            """DELETE from thumbnails
               where name=%(filename)s and
                     attached_to_pagename=%(pagename)s and
                     wiki_id=%(wiki_id)s""", dict, isWrite=True)

    # prep for insert of binary data
    if dict.has_key('filecontent'):
        raw_image = dict['filecontent']
        uploaded_time = dict['uploaded_time']
        dict['filecontent'] = dbapi.Binary(raw_image)

    page = Page(dict['pagename'], request)
    dict['pagename_propercased'] = page.proper_name()
    dict['pagename'] = dict['pagename'].lower()
    dict['wiki_id'] = request.config.wiki_id

    replaced_image = False
    is_image = isImage(dict['filename'])
      
    if temporary:
        # we don't update the database in this case
        set_cache_for_file()
        rebuild_page_cache()
        return

    if not thumbnail and not do_delete:
        handle_file_add()
    elif thumbnail and not do_delete:
        handle_thumbnail_add()
    elif do_delete:
        if not thumbnail:
            handle_file_delete()            
        else:
            handle_thumbnail_delete()

    set_cache_for_file()
    rebuild_page_cache()
    

class EditLine:
    def __init__(self, edit_tuple):
        self.pagename = edit_tuple[0]
        self.ed_time = edit_tuple[1]
        self.action = edit_tuple[3].strip()
        self.comment = edit_tuple[4]
        self.userid = edit_tuple[2]
        self.host = edit_tuple[5]
        self.wiki_name = None

    def __getstate__(self):
        """
        Used for pickling (marshalling).
        """
        return (self.pagename, self.ed_time, self.action, self.comment,
                self.userid, self.host, self.wiki_name)

    def __setstate__(self, unpickled_object):
        """
        Used for pickling (marshalling).
        """
        pagename, ed_time, action, comment, userid, host, wiki_name = \
            unpickled_object
        self.pagename = pagename
        self.ed_time = ed_time
        self.action = action
        self.comment = comment
        self.userid = userid
        self.host = host
        self.wiki_name = wiki_name


def getEditor(editLine, request):
     from Sycamore.user import User, getUserLink
     from Sycamore.Page import Page
     if editLine.userid and editLine.userid.strip():
        editUser = User(request, editLine.userid)
        return getUserLink(request, editUser, wiki_name=editLine.wiki_name,
                           show_title=False)
     else:
       return '<em>unknown</em>'

def _sort_changes_by_time(changes):
    def cmp_lines_edit(first, second):
        # in the case of file replacements, we want to show the upload
        #prior to the download
        # we do this in wikidb rather than recentchanges so that we cache
        # this state and use it for RSS, etc.
        if (first.ed_time == second.ed_time):
            if (first.action == 'ATTDEL' and second.action == 'ATTNEW'):
                return 1 
            elif (second.action == 'ATTDEL' and first.action == 'ATTNEW'):
                return -1
        return cmp(second.ed_time, first.ed_time)
    changes.sort(cmp_lines_edit)
    return changes

def filter_may_read(changes, request):
    # to reduce the number of method calls here.  People refresh RC a lot!
    readability_status = {} 
    def _filter_f(change):
        if readability_status.has_key((change.wiki_name, change.pagename)):
            return readability_status[(change.wiki_name, change.pagename)]
        request.switch_wiki(change.wiki_name)
        page = Page(change.pagename, request, wiki_name=change.wiki_name)
        status = request.user.may.read(page)
        readability_status[(change.wiki_name, change.pagename)] = status
        return status

    from Sycamore.Page import Page
    original_wiki = request.config.wiki_name
    filtered = filter(_filter_f, changes)
    request.switch_wiki(original_wiki)
    return filtered

def setRecentChanges(request, max_days=False, total_changes_limit=0,
                     per_page_limit='', page='', changes_since=0,
                     userFavoritesFor='', wiki_global=False):
    """
    We call this method to set the recent changes cache/s after a change
    has occured.
    """
    from wikiutil import mc_quote
    if config.memcache:
        if page:
            total_changes_limit = 100
        changes = getRecentChanges(
            request, max_days=max_days,
            total_changes_limit=total_changes_limit,
            per_page_limit=per_page_limit, page=page,
            changes_since=changes_since, userFavoritesFor=userFavoritesFor,
            wiki_global=wiki_global, fresh=True, add_to_cache=False,
            check_acl=False)
        request.mc.set('rc:%s' % mc_quote(page), changes)

def _get_changes_since(changetime, changes):
    """
    Given a sorted changes list, this returns all results since changetime.
    """
    since = []
    for change in changes:
        if change.ed_time < changetime:
            break
        since.append(change)
    return since

def getRecentChanges(request, max_days=False, total_changes_limit=0,
                     per_page_limit='', page='', changes_since=0,
                     userFavoritesFor='', wiki_global=False, fresh=False,
                     on_wikis=None, add_to_cache=True, check_acl=True):
    """
    This is our recent changes-getting method!
    The recentchanges.py macro does the pretty formatting.
    
    @param request: request object.
    @param max_days: integer number of max days to show on rc defaults to
        False if not given and we use RC_MAX_DAYS.
    @param total_changes_limit: integer limit on the total number of changes
        to return.  Defaults to 0 and we use ABSOLUTE_RC_CHANGES_LIMIT.
    @param per_page_limit: integer max for the number of changes per-page.
        Currently only supports the limit of 1.  Defaults to '', which means
        no intrinsic page limit.
    @param page: page object to limit the changes to.  Defaults to '', which
        means we grab changes on all pages.
    @param changes_since: grab only changes since this time
        (given as a unix timestamp).  Defaults to 0, which means we grab
        change back as far in time as makes sense.
    @param userFavoritesFor: user id of a user.  Providing this will grab all
        of the changes on the user's bookmarked pages.  Defaults to '', which
        means we just grab changes like usual.
    @param wiki_global: boolean.  If True, we grab changes across multiple
        wikis.  If False, we just grab changes on the current wiki.
    @param fresh: boolean.  If True then we don't grab any data from the cache.
        Defaults to False.
    @param on_wikis: a list of wiki names.  If provided then we grab changes
        on all of the wikis provided and mash them together.
            Defaults to None, which means we grab only the
            current wiki's changes.
    @param add_to_cache: boolean.  Defaults to True.  If True, we add the
        results of calling getRecentChanges() to the memory cache.
    @param check_acl: boolean.  Defaults to True.  If True, then we return
        only pages the user can read.
    @returns: None.
    """
    from wikiutil import mc_quote
    def addQueryConditions(view, query, max_days_ago, total_changes_limit,
                           per_page_limit, page, changes_since,
                           userFavoritesFor, wiki_global):
        """
        Limits the query in various ways.
        """
        add_query = []

        if per_page_limit:
            if view != 'eventChanges':
                add_query.append(
                    """(SELECT %(view)s.propercased_name as name,
                               max(%(view)s.changeTime) as changeTime,
                               %(view)s.id as id,
                               %(view)s.editType as editType,
                               %(view)s.comment as comment,
                               %(view)s.userIP as userIP
                        from %(view)s""" % {'view': view})
            else:
                add_query.append(
                    """(SELECT %(view)s.name as name,
                               max(%(view)s.changeTime) as changeTime,
                               %(view)s.id as id,
                               %(view)s.editType as editType,
                               %(view)s.comment as comment,
                               %(view)s.userIP as userIP
                        from %(view)s""" % {'view': view})
        else:
            if view != 'eventChanges':
                add_query.append(
                    """(SELECT %(view)s.propercased_name as name,
                               %(view)s.changeTime as changeTime,
                               %(view)s.id as id,
                               %(view)s.editType as editType,
                               %(view)s.comment as comment,
                               %(view)s.userIP as userIP from %(view)s""" % {'view': view})
            else:
                add_query.append(
                    """(SELECT %(view)s.name as name,
                               %(view)s.changeTime as changeTime,
                               %(view)s.id as id,
                               %(view)s.editType as editType,
                               %(view)s.comment as comment,
                               %(view)s.userIP as userIP from %(view)s""" % 
                    {'view': view})

        printed_where = False
        if page and not userFavoritesFor:
            add_query.append(
                """ where %(view)s.name=%%(pagename)s and
                          %(view)s.changeTime is not NULL and
                          wiki_id=%(wiki_id)s""" %
                {'view':view, 'wiki_id':request.config.wiki_id})
            printed_where = True

        if not printed_where:
            printed_where = True
            add_query.append(' where')
        else:
            add_query.append(' and')

        if max_days_ago:
            if changes_since:
                add_query.append(' changeTime >= %(changes_since)s and')
        else:
            if changes_since:
                add_query.append(' changeTime >= %(changes_since)s and')
          
        add_query.append(' wiki_id=%(wiki_id)s')

        if total_changes_limit and not per_page_limit:
            if not printed_where:
                add_query.append(' where')
            else:
                add_query.append(' and')

            add_query.append(
                """ changeTime is not NULL and
                    id is not NULL and
                    wiki_id=%%(wiki_id)s
                    order by changeTime desc limit %s)""" % total_changes_limit)
        elif not total_changes_limit and per_page_limit:
            pass
        else:
            add_query.append(')')
        
        query += add_query

    def buildQuery(max_days_ago, total_changes_limit, per_page_limit, page,
                   changes_since, userFavoritesFor, wiki_global, request):
        """
        Build up the big old recent changes query.
        """
        # we use a select statement on the outside here, though not needed,
        # so that MySQL will cache the statement.  MySQL does not cache
        # non-selects, so we have to do this.
        if per_page_limit:
            if config.db_type == 'postgres':
                query = [
                    'SELECT distinct on (name) name, changeTime, id, editType,'
                            'comment, userIP from ( SELECT * from ( ']
            elif config.db_type == 'mysql':
                query = [
                    """SELECT distinct (name), changeTime, id, editType,
                              comment, userIP
                       from ( SELECT * from ( """]
        else:
            query = [
                'SELECT name, changeTime, id, editType, comment,'
                'userIP from (']
        printed_where = False
        addQueryConditions('pageChanges', query, max_days_ago,
                           total_changes_limit, per_page_limit, page,
                           changes_since, userFavoritesFor, wiki_global)
        query.append(' UNION ALL ')
        addQueryConditions('currentFileChanges', query, max_days_ago,
                           total_changes_limit, per_page_limit, page,
                           changes_since, userFavoritesFor, wiki_global)
        query.append(' UNION ALL ')
        addQueryConditions('oldFileChanges', query, max_days_ago,
                           total_changes_limit, per_page_limit, page,
                           changes_since, userFavoritesFor, wiki_global)
        query.append(' UNION ALL ')
        addQueryConditions('deletedFileChanges', query, max_days_ago,
                           total_changes_limit, per_page_limit, page,
                           changes_since, userFavoritesFor, wiki_global)
        query.append(' UNION ALL ')
        addQueryConditions('eventChanges', query, max_days_ago,
                           total_changes_limit,  per_page_limit, page,
                           changes_since, userFavoritesFor, wiki_global)
        query.append(' UNION ALL ')
        addQueryConditions('oldMapChanges', query, max_days_ago,
                           total_changes_limit, per_page_limit, page,
                           changes_since, userFavoritesFor, wiki_global)
        query.append(' UNION ALL ')
        addQueryConditions('currentMapChanges', query, max_days_ago,
                           total_changes_limit, per_page_limit, page,
                           changes_since, userFavoritesFor, wiki_global)

        if request.config.has_old_wiki_map:
            query.append(' UNION ALL ')
            addQueryConditions('deletedMapChanges', query, max_days_ago,
                               total_changes_limit, per_page_limit, page,
                               changes_since, userFavoritesFor, wiki_global)

        if not per_page_limit:
            query.append(' order by changeTime desc')

        if total_changes_limit:
            query.append(' limit %(limit)s) as result')
        else:
            if per_page_limit:
                query.append(
                   " ) as sortedChanges order by changeTime desc ) as result")
            else:
              query.append(') as result')

        return ''.join(query)

    def get_interwiki_recent_changes():
        """
        we're doing an interwiki recent changes so we get rc for each wiki
        in on_wikis list.
        we use get_multi here.
        """
        changes = []
        original_wiki = request.config.wiki_name

        if not userFavoritesFor:
            wiki_keys = {}
            id_to_name = {}
            for wiki_name in on_wikis:
                request.switch_wiki(wiki_name)
                id_to_name[request.config.wiki_id] = wiki_name
                wiki_keys['%src:%s' %
                    (request.config.wiki_id, mc_quote(page))] = None
            # switch back to our original wiki
            if request.config.wiki_name != original_wiki:
                request.switch_wiki(original_wiki)

            if config.memcache and not fresh:
                values = request.mc.get_multi(wiki_keys.keys(),
                                              wiki_global=True)
                for k, got_changes in values.iteritems():
                    if got_changes is not None:
                        if total_changes_limit:
                            got_changes = got_changes[:total_changes_limit]
                        if changes_since:
                            got_changes = _get_changes_since(changes_since,
                                                             got_changes)
                        changes += got_changes

                        wiki_keys[k] = got_changes

            for key in wiki_keys:
                if wiki_keys[key] is None:
                    wiki_id = int(key[:key.find('rc:')])
                    request.switch_wiki(id_to_name[wiki_id])
                    changes += getRecentChanges(request, wiki_global=False,
                                               changes_since=changes_since,
                                               check_acl=check_acl)    

        else:
            request.switch_wiki(wiki_name)
            changes += getRecentChanges(request, wiki_global=False,
                                        changes_since=changes_since,
                                        check_acl=check_acl)    

        # switch back to our original wiki
        if request.config.wiki_name != original_wiki:
            request.switch_wiki(original_wiki)
        changes = _sort_changes_by_time(changes)
        changes = changes[:ABSOLUTE_RC_CHANGES_LIMIT] # for consistency's sake
        if check_acl:
            changes = filter_may_read(changes, request)
        return changes

    def get_user_favorites():
        from Sycamore import user
        changes = []
        original_wiki = request.config.wiki_name
        favlist = user.User(request, userFavoritesFor).getFavoriteList(
            wiki_global=wiki_global)
        for favorite in favlist:
            wiki_name = favorite.wiki_name
            request.switch_wiki(wiki_name)
            changes += getRecentChanges(request, page=favorite.page_name,
                                        total_changes_limit=1,
                                        wiki_global=False, check_acl=check_acl)
        # switch back to our original wiki
        if request.config.wiki_name != original_wiki:
            request.switch_wiki(original_wiki)
        changes = _sort_changes_by_time(changes)
        if check_acl:
            changes = filter_may_read(changes, request)
        return changes

    if not userFavoritesFor and on_wikis is None and not fresh:
        changes = None
        if config.memcache:
          changes = request.mc.get('rc:%s' % mc_quote(page))
          if changes is not None:
              if total_changes_limit:
                  changes = changes[:total_changes_limit]
              if changes_since:
                  changes = _get_changes_since(changes_since, changes)
              if check_acl:
                  changes = filter_may_read(changes, request)
              return changes

    elif on_wikis is not None:
        return get_interwiki_recent_changes()
        
    elif userFavoritesFor:
        return get_user_favorites()
        
    # We have to get the 'normal' recent changes, as this isn't a special
    # case and it wasn't in the cache.
    lines = []
    right_now  = time.gmtime()
    # we limit recent changes to display at most the last max_days of edits.
    if max_days:
        # the subtraction of max days is okay here, as mktime
        # will do the right thing
        oldest_displayed_time_tuple = (right_now[0], right_now[1],
                                       right_now[2]-max_days, 0, 0, 0, 0, 0, 0)
        max_days_ago = time.mktime(oldest_displayed_time_tuple)
    else:
        max_days_ago = False

    # still grab all the maximum days, and then limit them
    # after grabing (more efficient on the whole)
    if not userFavoritesFor and not page:
        query_max_days = time.mktime((right_now[0], right_now[1],
                                      right_now[2]-RC_MAX_DAYS, 0, 0, 0, 0, 0,
                                      0))
    else:
        query_max_days = max_days_ago

    query_total_changes_limit = total_changes_limit
    # by default for a per-page, grab total_changes_limit = 100
    if page and not total_changes_limit:
        query_total_changes_limit = 100
        total_changes_limit = 100
    elif not page and total_changes_limit and not userFavoritesFor:
        # we're doing RC or something close, so let's query for all
        query_total_changes_limit = 0 
    elif total_changes_limit <= ABSOLUTE_RC_CHANGES_LIMIT:
        query_total_changes_limit = ABSOLUTE_RC_CHANGES_LIMIT

    # so, let's compile all the different types of changes together!
    query = buildQuery(query_max_days, query_total_changes_limit,
                       per_page_limit, page, None, userFavoritesFor,
                       wiki_global, request)
    request.cursor.execute(query, {'max_days_ago': query_max_days, 
                                   'limit': query_total_changes_limit, 
                                   'userFavoritesFor': userFavoritesFor, 
                                   'pagename': page, 
                                   'changes_since':None, 
                                   'wiki_id': request.config.wiki_id})
 
    edit = request.cursor.fetchone()
    
    while edit:
        editline = EditLine(edit)
        editline.wiki_name = request.config.wiki_name
        lines.append(editline)
        edit = request.cursor.fetchone()

    lines = _sort_changes_by_time(lines) 

    if config.memcache and add_to_cache:
        request.mc.add('rc:%s' % mc_quote(page), lines)

        # deepcopy here because sometimes people do
        # lines.comment = something, and we want to add the
        # 'real' data to the cache (postCommit, so it happens way later)
        lines = copy.deepcopy(lines) 

    if total_changes_limit:
        lines = lines[:total_changes_limit]

    if changes_since:
        lines = _get_changes_since(changes_since, lines)
    if check_acl:
        lines = filter_may_read(lines, request)

    return lines

def getPageCount(request):
    """
    Returns the number of current (alive, not deleted) pages in the wiki.
    """
    page_count = None
    if config.memcache:
        # check memcache
        page_count = request.mc.get('active_page_count')
    if page_count is None:
        cursor = request.cursor
        cursor.execute("""SELECT count(name) from curPages
            where wiki_id=%(wiki_id)s""", {'wiki_id':request.config.wiki_id})
        page_count = cursor.fetchone()[0]
        if config.memcache:
            request.mc.add('active_page_count', page_count)
    
    return page_count
