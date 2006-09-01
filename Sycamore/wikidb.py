# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Wiki MySQL support functions

    @copyright: 2005 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

# User calls wikidb.connect() to get a WikiDB object.

# Imports
from Sycamore import config
from Sycamore.support import pool
import time, array

if config.db_type == 'mysql':
  dbapi_module = __import__("MySQLdb")
elif config.db_type == 'postgres':
  dbapi_module = __import__("psycopg2")

pool_size = config.db_pool_size
max_overflow = config.db_max_overflow

Binary = dbapi_module.Binary
dbapi = pool.manage(dbapi_module, pool_size=pool_size, max_overflow=max_overflow)
dbapi.Binary = Binary

def fixUpStrings(item):
  def doFixUp(i):
    if type(i) == array.array:
      return i.tostring()
    elif type(i) == str:
      return i.decode(config.db_charset)
    elif type(i) == tuple:
      return fixUpStrings(i)
    return i

  if type(item) == tuple or type(item) == list:
    return [ doFixUp(i) for i in item ]
  return doFixUp(item)
      

class WikiDB(object):
  def __init__(self, db):
    self.db = db
    self.do_commit = False

  def close(self):
    if config.db_type == 'mysql':
        try:
            self.db.close()
        except dbapi_module.OperationalError, (errno, strerror):
            if errno == 2006:
                del self.db.db
                # just pass, essentially
            else:
                raise dbapi_module.OperationalError, x
    else:
        self.db.close()

    del self.db
  
  def cursor(self):
    # TODO: need to make sure we set autocommit off in other dbs
    return WikiDBCursor(self)
  
  def commit(self):
    self.db.commit()

  def rollback(self):
    if self.db:
        if config.db_type == 'mysql':
            try:
                self.db.rollback()
            except dbapi_module.OperationalError, (errno, strerror):
                if errno == 2006:
                    del self.db.db
                    # just pass, essentially
                else:
                    raise dbapi_module.OperationalError, x

class WikiDBCursor(object):
  def __init__(self, db):
    self.db = db
    if db.db: self.db_cursor = db.db.cursor()
    else: self.db_cursor = None

  def execute(self, query, args={}, isWrite=False):
    if not self.db.db:
      # connect to the db for real for the first time 
      self.db.db = real_connect()
      self.db_cursor = self.db.db.cursor()

    if isWrite:
      self.db.do_commit = True
    if args: args = _fixArgs(args)

    if config.db_type == 'mysql':
        try:
            self.db_cursor.execute(query, args) 
        except dbapi_module.OperationalError, (errno, strerror):
            if errno == 2006:
                    self.db.ping()
                    self.db_cursor.execute(query, args) 
            else:
                raise dbapi_module.OperationalError, x
    else:
        self.db_cursor.execute(query, args) 

  def executemany(self, query, args_seq=(), isWrite=False):
    if not self.db.db:
      # connect to the db for real for the first time 
      self.db.db = real_connect()
      self.db_cursor = self.db.db.cursor()

    if isWrite:
      self.db.do_commit = True
    if args_seq:
      args_seq = [ _fixArgs(arg) for arg in args_seq ]

    if config.db_type == 'mysql':
            try:
                self.db_cursor.executemany(query, args_seq) 
            except dbapi_module.OperationalError, (errno, strerror):
                if errno == 2006:
                    self.db.ping()
                    self.db_cursor.executemany(query, args_seq) 
                else:
                    raise dbapi_module.OperationalError, x
    else:
        self.db_cursor.executemany(query, args_seq) 

  def fetchone(self):
    return fixUpStrings(self.db_cursor.fetchone())

  def fetchall(self):
     return fixUpStrings(self.db_cursor.fetchall())

  def close(self):
    if self.db_cursor:
        if config.db_type == 'mysql':
            try:
                self.db_cursor.close()
            except dbapi_module.OperationalError, (errno, strerror):
                if errno == 2006:
                    self.db_cursor.close()
                else:
                    raise dbapi_module.OperationalError, x
        else:
            self.db_cursor.close()
        del self.db_cursor
    return

def _fixArgs(args):
    # Converts python floats to limited-precision float strings
    #  before sending them to the db.  This is so that we can 
    #  keep the precision consistent between implementations.
    #  (I am not sure of a more elegant way to do this without using a specialized mysql type.)
    #  (This at least keeps consistency and keeps the accidential programmer from being throw off by 
    #  weird floating point issues)
    #  The idea is that we limit the length of our floats to be five places after the decimal point.
    #  Python's floats are bigger than this, and so are mysql's.  So we know that our internal rounding
    #  will work and be consistent between the two.

    def fixValue(o):
      if type(o) == float: return _floatToString(o)
      else: return o
    
    # is args a sequence?
    #if type(args) == type([]) or type(args) == type((1,)):
    #  args = map(fixValue, args)
    new_args = {}
    for k, v in args.iteritems():
      new_args[k] = fixValue(v) 
        
    return new_args

def _floatToString(f):
  # converts a float to the proper length of double that mysql uses.
  # we need to use this when we render a link (GET/POST) that displays a double from the db, because python's floats are bigger than mysql's floats
  return "%.5f" % f

def binaryToString(b):
  # converts a binary format (as returned by the db) to a string.  Different modules do this differently :-/
  if config.db_type == 'postgres':
    return str(b)
  elif config.db_type == 'mysql':
    if not hasattr(b, 'tostring'): return b
    return b.tostring()

def connect():
  return WikiDB(None)

def real_connect():
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
        if errno == 2006:
            had_error = True
            while had_error:
                db.alive = False
                del db
                db = dbapi.connect(**d)
                # keep trying to get a good connection from the pool
                try:
                    db.ping()
                except dbapi_module.OperationalError, (errno, strerror):
                    if errno == 2006:
                        had_error = True
                    else:
                        had_error = False
                else:
                    had_error = False
        else:
            raise dbapi_module.OperationalError, x
  
  return db

def getFile(request, dict, deleted=False, thumbnail=False, version=0, ticket=None, size=None):
  """
  dict is a dictionary with possible keys: filename, page_name, and file_version.
  """
  from Sycamore.wikiutil import quoteFilename
  file_obj = False
  dict['page_name'] = dict['page_name'].lower()

  # let's assemble the query and key if we use memcache
  if not deleted and not thumbnail and not version:
    if config.memcache:
      key = "files:%s,%s" % (quoteFilename(dict['filename']), quoteFilename(dict['page_name']))
    query = "SELECT file, uploaded_time from files where name=%(filename)s and attached_to_pagename=%(page_name)s"
  elif thumbnail:
    if not ticket:
      if config.memcache:
        key = "thumbnails:%s,%s" % (quoteFilename(dict['filename']), quoteFilename(dict['page_name']))
      query = "SELECT image, last_modified from thumbnails where name=%(filename)s and attached_to_pagename=%(page_name)s"
    else: 
      if config.memcache:
        key = "thumbnails:%s,%s" % (quoteFilename(dict['filename']), size or ticket)
  elif deleted:
    if not version:
      # default behavior is to grab the latest backup version of the image
      if config.memcache:
        key = "oldfiles:%s,%s" % (quoteFilename(dict['filename']), quoteFilename(dict['page_name']))
      query = "SELECT file, uploaded_time from oldFiles where name=%(filename)s and attached_to_pagename=%(page_name)s order by uploaded_time desc;"
    elif version:
      if config.memcache:
        key = "oldfiles:%s,%s,%s" % (quoteFilename(dict['filename']), quoteFilename(dict['page_name']), version)
      query = "SELECT file, uploaded_time from oldFiles where name=%(filename)s and attached_to_pagename=%(page_name)s and uploaded_time=%(file_version)s"

  if config.memcache:
    file_obj = request.mc.get(key)

  if not file_obj:
    from wikiutil import isImage
    if ticket and isImage(dict['filename']):
       # we generate the thumbnail..weee
       from Sycamore.macro import image
       file_obj = (image.generateThumbnail(request, dict['page_name'], dict['filename'], dict['maxsize'], return_image=True) , 0)
    else:
       request.cursor.execute(query, dict)
       file_obj = request.cursor.fetchone()
       if not file_obj:
         raise 'DBNoContent'
       #Messy because of a bug in python for pickling array.array -- must convert to str before putting in memcache
       new_file_obj = (binaryToString(file_obj[0]), file_obj[1])
       file_obj = new_file_obj
       
    if config.memcache:
      request.mc.add(key, file_obj)

  return file_obj[0], file_obj[1]

def putFile(request, dict, thumbnail=False, do_delete=False, temporary=False, ticket=None):
  """
  Puts the file (found in dict) into the database. dict is a dictionary with possible keys: filename, filecontent, uploaded_time, uploaded_by, pagename, uploaded_by_ip, xsize, ysize, deleted_time, deleted_by, deleted_by_ip
  """
  from Sycamore.wikiutil import quoteFilename, isImage
  from Sycamore.Page import Page
  from Sycamore.action.Files import get_filedict
  # prep for insert of binary data
  if dict.has_key('filecontent'):
    raw_image = dict['filecontent']
    uploaded_time = dict['uploaded_time']
    dict['filecontent'] = dbapi.Binary(raw_image)
  dict['pagename_propercased'] = Page(dict['pagename'], request).proper_name()
  dict['pagename'] = dict['pagename'].lower()
  replaced_image = False
  is_image = isImage(dict['filename'])
    
  if not temporary:
    if not thumbnail and not do_delete:
      request.cursor.execute("SELECT name from files where name=%(filename)s and attached_to_pagename=%(pagename)s", dict)
      exists = request.cursor.fetchone()
      if exists:
        # backup file, then remove it  
        dict['timenow'] = time.time()
        replaced_image = True
        request.cursor.execute("INSERT into oldFiles (name, file, uploaded_time, uploaded_by, attached_to_pagename, deleted_time, deleted_by, uploaded_by_ip, deleted_by_ip, attached_to_pagename_propercased) values (%(filename)s, (select file from files where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_time from files where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_by from files where name=%(filename)s and attached_to_pagename=%(pagename)s), %(pagename)s, %(timenow)s, %(uploaded_by)s, (select uploaded_by_ip from files where name=%(filename)s and attached_to_pagename=%(pagename)s), %(uploaded_by_ip)s, %(pagename_propercased)s)", dict, isWrite=True)
        if is_image:
          request.cursor.execute("INSERT into oldImageInfo (name, attached_to_pagename, xsize, ysize, uploaded_time) values (%(filename)s, %(pagename)s, (select xsize from imageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s), (select ysize from imageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_time from files where name=%(filename)s and attached_to_pagename=%(pagename)s))", dict, isWrite=True)
          request.cursor.execute("DELETE from imageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s", dict, isWrite=True)

        request.cursor.execute("DELETE from files where name=%(filename)s and attached_to_pagename=%(pagename)s", dict, isWrite=True)

      request.cursor.execute("INSERT into files (name, file, uploaded_time, uploaded_by, attached_to_pagename, uploaded_by_ip, attached_to_pagename_propercased) values (%(filename)s, %(filecontent)s, %(uploaded_time)s, %(uploaded_by)s, %(pagename)s, %(uploaded_by_ip)s, %(pagename_propercased)s)", dict, isWrite=True)
      if is_image:
        request.cursor.execute("INSERT into imageInfo (name, attached_to_pagename, xsize, ysize) values (%(filename)s, %(pagename)s, %(xsize)s, %(ysize)s)", dict, isWrite=True)
    elif thumbnail and not do_delete:
      request.cursor.execute("SELECT name from thumbnails where name=%(filename)s and attached_to_pagename=%(pagename)s", dict)
      exists = request.cursor.fetchone()
      if exists:
        request.cursor.execute("UPDATE thumbnails set xsize=%(x)s, ysize=%(y)s, image=%(filecontent)s, last_modified=%(uploaded_time)s where name=%(filename)s and attached_to_pagename=%(pagename)s", dict, isWrite=True)
      else:
        request.cursor.execute("INSERT into thumbnails (xsize, ysize, name, image, last_modified, attached_to_pagename) values (%(x)s, %(y)s, %(filename)s, %(filecontent)s, %(uploaded_time)s, %(pagename)s)", dict, isWrite=True)
    elif do_delete:
      if not thumbnail:
        request.cursor.execute("SELECT name from files where name=%(filename)s and attached_to_pagename=%(pagename)s", dict)
        has_file = request.cursor.fetchone()
        if has_file:
          # backup file  
          request.cursor.execute("INSERT into oldFiles (name, attached_to_pagename, file, uploaded_by, uploaded_time, deleted_time, deleted_by, uploaded_by_ip, deleted_by_ip, attached_to_pagename_propercased) values (%(filename)s, %(pagename)s, (select file from files where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_by from files where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_time from files where name=%(filename)s and attached_to_pagename=%(pagename)s), %(deleted_time)s, %(deleted_by)s, (select uploaded_by_ip from files where name=%(filename)s and attached_to_pagename=%(pagename)s), %(deleted_by_ip)s, (select attached_to_pagename_propercased from files where name=%(filename)s and attached_to_pagename=%(pagename)s))", dict, isWrite=True)

          if is_image:
            # backup image info
            request.cursor.execute("INSERT into oldImageInfo (name, attached_to_pagename, xsize, ysize, uploaded_time) values (%(filename)s, %(pagename)s, (select xsize from imageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s), (select ysize from imageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_time from files where name=%(filename)s and attached_to_pagename=%(pagename)s))", dict, isWrite=True)
            # delete image info
            request.cursor.execute("DELETE from imageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s", dict, isWrite=True)

          # delete file 
          request.cursor.execute("DELETE from files where name=%(filename)s and attached_to_pagename=%(pagename)s", dict, isWrite=True)
      else:
        # delete thumbnail
        request.cursor.execute("DELETE from thumbnails where name=%(filename)s and attached_to_pagename=%(pagename)s", dict, isWrite=True)

  if config.memcache:
    if not do_delete:
      if not thumbnail: table = 'files'
      else: table = 'thumbnails'
      if not temporary:
        key = "%s:%s,%s" % (table, quoteFilename(dict['filename']), quoteFilename(dict['pagename'].lower()))
      else:
        key = "%s,%s,%s" % (table, quoteFilename(dict['filename']), ticket)
      image_obj = (raw_image, uploaded_time)
      request.mc.set(key, image_obj)
    else:
      key = "files:%s,%s" % (quoteFilename(dict['filename']), quoteFilename(dict['pagename'].lower()))
      request.mc.delete(key)
      if is_image:
        key = "thumbnails:%s,%s" % (quoteFilename(dict['filename']), quoteFilename(dict['pagename'].lower()))
        request.mc.delete(key)

    # set new file dict
    if not replaced_image:
      get_filedict(request, dict['pagename'], fresh=True, set=True)

  # rebuild the page cache
  if not request.generating_cache and not request.previewing_page:
    from Sycamore import caching
    from Sycamore.Page import Page
    #caching.CacheEntry(dict['pagename'], request).clear()
    page = Page(dict['pagename'], request)
    if page.exists():
      page.buildCache()

def getRecentChanges(request, max_days=False, total_changes_limit=0, per_page_limit='', page='', changes_since=0, userFavoritesFor=''):
  # betta' with this line object so we can move away from array indexing
  def addQueryConditions(view, query, max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor):
    add_query = []
    if per_page_limit and userFavoritesFor:
       if view != 'eventChanges':
         add_query.append("""
         SELECT groupedChanges.name as name, groupedChanges.changeTime as changeTime, %(view)s.id as id, %(view)s.editType as editType, %(view)s.comment as comment, %(view)s.userIP as userIP from
         (
            SELECT %(view)s.propercased_name as name, max(%(view)s.changeTime) as changeTime from %(view)s, userFavorites as f, users as u where u.name=f.username and f.page=%(view)s.name and u.id=%%(userFavoritesFor)s group by %(view)s.propercased_name
         ) as groupedChanges, %(view)s where groupedChanges.name=%(view)s.propercased_name and groupedChanges.changeTime=%(view)s.changeTime and groupedChanges.changeTime is not NULL
         """ % {'view': view} )
       else:
         add_query.append("""
            SELECT groupedChanges.name as name, groupedChanges.changeTime as changeTime, %(view)s.id as id, %(view)s.editType as editType, %(view)s.comment as comment, %(view)s.userIP as userIP from
            (
               SELECT %(view)s.name as name, max(%(view)s.changeTime) as changeTime from %(view)s, userFavorites as f, users as u where u.name=f.username and f.page=%(view)s.name and u.id=%%(userFavoritesFor)s group by %(view)s.name
            ) as groupedChanges, %(view)s where groupedChanges.name=%(view)s.name and groupedChanges.changeTime=%(view)s.changeTime and groupedChanges.changeTime is not NULL
            """ % {'view': view} )

    elif per_page_limit:
       if view != 'eventChanges':
         add_query.append("(SELECT %(view)s.propercased_name as name, max(%(view)s.changeTime) as changeTime, %(view)s.id as id, %(view)s.editType as editType, %(view)s.comment as comment, %(view)s.userIP as userIP from %(view)s" % {'view': view})
       else:
         add_query.append("(SELECT %(view)s.name as name, max(%(view)s.changeTime) as changeTime, %(view)s.id as id, %(view)s.editType as editType, %(view)s.comment as comment, %(view)s.userIP as userIP from %(view)s" % {'view': view})
    else:
       if view != 'eventChanges':
         add_query.append("(SELECT %(view)s.propercased_name as name, %(view)s.changeTime as changeTime, %(view)s.id as id, %(view)s.editType as editType, %(view)s.comment as comment, %(view)s.userIP as userIP from %(view)s" % {'view': view})
       else:
         add_query.append("(SELECT %(view)s.name as name, %(view)s.changeTime as changeTime, %(view)s.id as id, %(view)s.editType as editType, %(view)s.comment as comment, %(view)s.userIP as userIP from %(view)s" % {'view': view})

    printed_where = False
    if page and not userFavoritesFor:
      add_query.append(' where %(view)s.name=%%(pagename)s and %(view)s.changeTime is not NULL' % {'view':view})
      printed_where = True

    if max_days_ago:
      if not printed_where:
        if not changes_since:
          add_query.append(' where changeTime >= %(max_days_ago)s')
        else: 
          add_query.append(' where changeTime >= %(max_days_ago)s and changeTime >= %(changes_since)s')
	printed_where = True
      else:
        if not changes_since: 
          add_query.append(' and changeTime >= %(max_days_ago)s')
 	else:
          add_query.append(' and changeTime >= %(max_days_ago)s and changeTime >= %(changes_since)s')
    #if per_page_limit:
    #  query.append(" group by %(view)s.name, %(view)s.id, %(view)s.editType, %(view)s.comment, %(view)s.userIP" % {'view':view})
    if total_changes_limit and not per_page_limit:
      if not printed_where:
        add_query.append(" where changeTime is not NULL order by changeTime desc limit %s)" % total_changes_limit)
      else:
        add_query.append(" and changeTime is not NULL order by changeTime desc limit %s)" % total_changes_limit)

    elif not total_changes_limit and per_page_limit:
      pass
    elif page:
      add_query.append(')')
    else:
      add_query.append(')')
    
    query += add_query

  def buildQuery(max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor):
    # we use a select statement on the outside here, though not needed, so that MySQL will cache the statement.  MySQL does not cache non-selects, so we have to do this.
    if per_page_limit:
      if config.db_type == 'postgres':
        query = ['SELECT distinct on (name) name, changeTime, id, editType, comment, userIP from ( SELECT * from ( ']
      elif config.db_type == 'mysql':
        query = ['SELECT distinct (name), changeTime, id, editType, comment, userIP from ( SELECT * from ( ']
    else:
      query = ['SELECT name, changeTime, id, editType, comment, userIP from (']
    printed_where = False
    addQueryConditions('pageChanges', query, max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor)
    query.append(' UNION ALL ')
    addQueryConditions('currentFileChanges', query, max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor)
    query.append(' UNION ALL ')
    addQueryConditions('oldFileChanges', query, max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor)
    query.append(' UNION ALL ')
    addQueryConditions('deletedFileChanges', query, max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor)
    query.append(' UNION ALL ')
    addQueryConditions('eventChanges', query, max_days_ago, total_changes_limit,  per_page_limit, page, changes_since, userFavoritesFor)
    query.append(' UNION ALL ')
    addQueryConditions('currentMapChanges', query, max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor)
    query.append(' UNION ALL ')
    addQueryConditions('oldMapChanges', query, max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor)
    query.append(' UNION ALL ')
    addQueryConditions('deletedMapChanges', query, max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor)

    if not per_page_limit: query.append(' order by changeTime desc')

    if total_changes_limit: query.append(' limit %(limit)s) as result')
    else:
      if per_page_limit:
	query.append(""" ) as sortedChanges order by changeTime desc ) as result""")
      else:
        query.append(') as result')

      #if per_page_limit: query.append(' group by name')

    return ''.join(query)

  class line:
    def __init__(self, edit_tuple):
      self.pagename = edit_tuple[0]
      self.ed_time = edit_tuple[1]
      self.action = edit_tuple[3].strip()
      self.comment = edit_tuple[4]
      self.userid = edit_tuple[2]
      self.host = edit_tuple[5]

    def getEditor(self, request):
         from Sycamore import user
	 from Sycamore.Page import Page
         if self.userid and self.userid.strip():
           editUser = user.User(request, self.userid)
           return user.getUserLink(request, editUser)
         else:
	   return '<em>unknown</em>'

  lines = []
  right_now  = time.gmtime()
  # we limit recent changes to display at most the last max_days of edits.
  if max_days:
    oldest_displayed_time_tuple = (right_now[0], right_now[1], right_now[2]-max_days, 0, 0, 0, 0, 0, 0)
    max_days_ago = time.mktime(oldest_displayed_time_tuple)
  else: max_days_ago = False

  # b/c oldest_time is the same until it's a new day, this statement caches well
  # so, let's compile all the different types of changes together!
  query = buildQuery(max_days_ago, total_changes_limit, per_page_limit, page, changes_since, userFavoritesFor)
  #print query % {'max_days_ago': '"'+str(max_days_ago)+'"', 'limit': '"'+str(total_changes_limit)+'"', 'userFavoritesFor': '"'+str(userFavoritesFor)+'"', 'pagename': '"'+str(page)+'"'}
  #print query % {'max_days_ago': '\''+str(max_days_ago)+'\'', 'limit': '\''+str(total_changes_limit)+'\'', 'userFavoritesFor': '\''+str(userFavoritesFor)+'\'', 'pagename': '\''+str(page)+'\''}
  request.cursor.execute(query, {'max_days_ago': max_days_ago, 'limit': total_changes_limit, 'userFavoritesFor': userFavoritesFor, 'pagename': page, 'changes_since':changes_since})
 
  edit = request.cursor.fetchone()
  
  while edit:
    lines.append(line(edit))
    edit = request.cursor.fetchone()
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
     cursor.execute("SELECT count(name) from curPages")
     page_count = cursor.fetchone()[0]
     if config.memcache:
       request.mc.add('active_page_count', page_count)
   return page_count
