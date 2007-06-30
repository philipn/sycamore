import sys, cStringIO, os, shutil, re
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])

from Sycamore import wikiutil, config, request, caching, wikidb, maintenance, buildDB, wikiacl, maintenance
from Sycamore.Page import Page

#################################################
# This script will 'merge' a series of wikis
# into a master wiki.  Make sure your
# sycamore_config.py points to the master wiki.
#
# You need to have run wikis.py before running
# this.
#################################################

# uncomment me and use the format written here
#wikis_to_merge = [ {'db_name':'projectsycamore', 'db_user':'projectsycamore', 'db_user_password':'wiki'} , {'db_name':'anotherwiki', 'db_user':'anotherusername', 'db_user_password':'passwordhere'}]

wikis_to_merge = [
    {'db_name':'rocwikicopy', 'db_user':'postgres', 'db_user_password':''},
    {'db_name':'daviswikicopy', 'db_user':'postgres', 'db_user_password':''},
    {'db_name':'projectsycamorecopy', 'db_user':'postgres', 'db_user_password':''},
    {'db_name':'anthillcopy', 'db_user':'postgres', 'db_user_password':''},
    {'db_name':'scwikicopy', 'db_user':'postgres', 'db_user_password':''},
    {'db_name':'pghwikicopy', 'db_user':'postgres', 'db_user_password':''},
    {'db_name':'chicowikicopy', 'db_user':'postgres', 'db_user_password':''},
]

tables = [ 
    ('curPages', ('name', 'text', 'cachedText', 'editTime', 'cachedTime', 'userEdited', 'propercased_name', 'wiki_id')),
    ('allPages', ('name', 'text', 'editTime', 'userEdited', 'editType', 'comment', 'userIP', 'propercased_name', 'wiki_id')),
    ('users', ('id', 'name', 'email', 'enc_password', 'language', 'remember_me', 'css_url', 'disabled', 'edit_cols', 'edit_rows', 'edit_on_doubleclick', 'theme_name', 'last_saved', 'join_date', 'created_count', 'edit_count', 'file_count', 'last_page_edited', 'last_edit_date', 'rc_bookmark', 'rc_showcomments', 'tz', 'propercased_name', 'last_wiki_edited', 'wiki_for_userpage')),
    ('userFavorites', ('username', 'page', 'viewTime', 'wiki_name')),
    ('userWatchedWikis', ('username', 'wiki_name')),
    ('userSessions', ('user_id', 'session_id', 'secret', 'expire_time')),
    ('links', ('source_pagename', 'destination_pagename', 'destination_pagename_propercased', 'wiki_id')),
    ('events', ('uid', 'event_time', 'posted_by', 'text', 'location', 'event_name', 'posted_by_ip', 'posted_time', 'wiki_id')),
    ('files', ('name', 'file', 'uploaded_time', 'uploaded_by', 'attached_to_pagename', 'uploaded_by_ip', 'attached_to_pagename_propercased', 'wiki_id')),
    ('oldFiles', ('name', 'file', 'uploaded_time', 'uploaded_by', 'attached_to_pagename', 'deleted_time', 'deleted_by', 'uploaded_by_ip', 'deleted_by_ip', 'attached_to_pagename_propercased', 'wiki_id')),
    ('thumbnails', ('xsize', 'ysize', 'name', 'attached_to_pagename', 'image', 'last_modified', 'wiki_id')),
    ('imageInfo', ('name', 'attached_to_pagename', 'xsize', 'ysize', 'wiki_id')),
    ('oldImageInfo', ('name', 'attached_to_pagename', 'xsize', 'ysize', 'uploaded_time', 'wiki_id')),
    ('imageCaptions', ('image_name', 'attached_to_pagename', 'linked_from_pagename', 'caption', 'wiki_id')),
    ('mapCategoryDefinitions', ('id', 'img', 'name', 'wiki_id')),
    ('mapPoints', ('pagename', 'x', 'y', 'created_time', 'created_by', 'created_by_ip', 'id', 'pagename_propercased', 'address', 'wiki_id')),
    ('oldMapPoints', ('pagename', 'x', 'y', 'created_time', 'created_by', 'created_by_ip', 'deleted_time', 'deleted_by_ip', 'pagename_propercased', 'address', 'wiki_id')),
    ('mapPointCategories', ('pagename', 'x', 'y', 'id', 'wiki_id')),
    ('oldMapPointCategories', ('pagename', 'x', 'y', 'id', 'deleted_time', 'wiki_id')),
    ('pageDependencies', ('page_that_depends', 'source_page', 'wiki_id')),
    ('metadata', ('pagename', 'type', 'name', 'value', 'wiki_id')),
    ('wikis', ('id', 'name', 'domain', 'is_disabled', 'sitename', 'other_settings')),
    ('userWikiInfo', ('user_name', 'wiki_id', 'first_edit_date', 'created_count', 'edit_count', 'file_count', 'last_page_edited', 'last_edit_date', 'rc_bookmark')),
    ('pageAcls', ('pagename', 'groupname', 'wiki_id', 'may_read', 'may_edit', 'may_delete', 'may_admin')),
    ('userGroups', ('username', 'groupname', 'wiki_id')),
    ('userGroupsIPs', ('ip', 'groupname', 'wiki_id')),
    ('lostPasswords', ('uid', 'code', 'written_time')), 
    ('wikisPending', ('wiki_name', 'code', 'written_time')),
    ('captchas', ('id', 'secret', 'human_readable_secret', 'written_time')),
]

tables_with_wiki_id = [
    'curPages',
    'allPages',
    'links',
    'events',
    'files',
    'oldFiles',
    'thumbnails',
    'imageInfo',
    'oldImageInfo',
    'imageCaptions',
    'mapCategoryDefinitions',
    'mapPoints',
    'oldMapPoints',
    'mapPointCategories',
    'oldMapPointCategories',
    'pageDependencies',
    'metadata',
    'userWikiInfo',
    'pageAcls',
    'userGroups',
    'userGroupsIPs',
]

def clear_user_sessions(request):
    request.cursor.execute("DELETE from userSessions", isWrite=True)

def update_uid(username, uid, wikis_to_merge):
    for wiki_dict in wikis_to_merge:
        cursor = wiki_dict['cursor']
        cursor.execute("SELECT id from users where name=%(username)s", {'username':username})
        old_uid_result = cursor.fetchone()
        if old_uid_result:
            old_uid = old_uid_result[0]
            d = {'uid':uid, 'old_uid':old_uid}
            cursor.execute("UPDATE curPages set userEdited=%(uid)s where userEdited=%(old_uid)s", d)
            cursor.execute("UPDATE allPages set userEdited=%(uid)s where userEdited=%(old_uid)s", d)
            cursor.execute("UPDATE files set uploaded_by=%(uid)s where uploaded_by=%(old_uid)s", d)
            cursor.execute("UPDATE oldFiles set uploaded_by=%(uid)s where uploaded_by=%(old_uid)s", d)
            cursor.execute("UPDATE oldFiles set deleted_by=%(uid)s where deleted_by=%(old_uid)s", d)
            cursor.execute("UPDATE mapPoints set created_by=%(uid)s where created_by=%(old_uid)s", d)
            cursor.execute("UPDATE oldMapPoints set created_by=%(uid)s where created_by=%(old_uid)s", d)
            cursor.execute("UPDATE oldMapPoints set deleted_by=%(uid)s where deleted_by=%(old_uid)s", d)


user_values = "id, name, email, enc_password, language, remember_me, css_url, disabled, edit_cols, edit_rows, edit_on_doubleclick, theme_name, last_saved, join_date, created_count, edit_count, file_count, last_page_edited, last_edit_date, rc_bookmark, rc_showcomments, tz, last_wiki_edited, propercased_name, wiki_for_userpage"

def insert_user(uid, cursor, request):
    cursor.execute("SELECT " + user_values + " from users where id=%(uid)s", {'uid':uid}) 
    userdata = cursor.fetchone()
    t, d = tuple_format(userdata)
    request.cursor.execute("SELECT name from users where name=%(1)s", d)
    result = request.cursor.fetchone()
    if result and result[0]:
    	# is in main wiki already. let's update.
	request.cursor.execute("DELETE from users where name=%(1)s", d)
    request.cursor.execute("INSERT into users (" + user_values + ") values %s" % t, d)


def find_canonical_users(wikis_to_merge, request):
    """
    Selects a single user from many users w/the same username.
    Decides based upon who made the oldest edit.
    """
    users = {}
    for wiki_dict in wikis_to_merge:
        cursor = wiki_dict['cursor']
        cursor.execute("SELECT name, last_edit_date from users")
        users_result = cursor.fetchall()
        for username, last_edit_date in users_result:
            if not users.has_key(username) or users[username][0] < last_edit_date:
                users[username] = (last_edit_date, wiki_dict)

    # do base wiki
    request.cursor.execute("SELECT name, last_edit_date from users")
    users_result = request.cursor.fetchall()
    for username, last_edit_date in users_result:
        # when dealing with hub users, we assume the merged-in user is
        # the 'real' user, and ignore the hub user of the same name
        if not users.has_key(username):
            users[username] = (last_edit_date, None)

    # grab canonical uids
    for username in users:
        wiki_dict = users[username][1]
        if not wiki_dict:
            cursor = request.cursor
        else:
            cursor = wiki_dict['cursor']
        cursor.execute("SELECT id from users where name=%(username)s", {'username':username})
        uid = cursor.fetchone()[0]
        # if already in db, no need to add again
        if wiki_dict:
            insert_user(uid, cursor, request)
        update_uid(username, uid, wikis_to_merge + [{'cursor':request.cursor}])

max_uid_events = 1

def set_incremented_values(request):
    d = {}
    request.cursor.execute("SELECT max(id) from wikis")
    result = request.cursor.fetchone()
    d['wikis_max'] = result[0]
    request.cursor.execute("SELECT max(uid) from events")
    result = request.cursor.fetchone()
    d['events_max'] = result[0]
    #request.cursor.execute("SELECT max(id) from mapPoints")
    #result = request.cursor.fetchone()
    #d['mapPoints_max'] = result[0]
    if config.db_type == 'postgres':
    	request.cursor.execute("SELECT setval('wikis_seq', %(wikis_max)s)", d, isWrite=True)
    	request.cursor.execute("SELECT setval('events_seq', %(events_max)s)", d, isWrite=True)
    #	request.cursor.execute("SELECT setval(mapPoints_seq, %(mapPoints_max)s)", isWrite=True)


def move_potential_uid_conflicts(wiki_cursor, req):
   global max_uid_events
   wiki_cursor.execute("SELECT uid, event_time, posted_by, text, location, event_name, posted_by_ip, posted_time, wiki_id from events")
   events = wiki_cursor.fetchall()
   i = 0
   for uid, event_time, posted_by, text, location, event_name, posted_by_ip, posted_time, wiki_id in events:
       if not uid: uid = 0
       i += 1
       wiki_cursor.execute("UPDATE events set uid=%(new_uid)s where uid=%(uid)s", {'uid': uid, 'new_uid': uid + max_uid_events})
   max_uid_events += i
    

def move_potential_wiki_id_conflicts(wiki_cursor, req):
    wiki_cursor.execute("SELECT id, name from wikis group by id, name")
    wiki_id, wiki_name = wiki_cursor.fetchone()
    req.cursor.execute("SELECT name from wikis where name=%(wiki_name)s", {'wiki_name':wiki_name})
    has_wiki_name = req.cursor.fetchone()
    if has_wiki_name:
    	# nuke the test wiki somebody made
    	wiki_cursor.execute("DELETE from wikis where name=%(wiki_name)s", {'wiki_name':wiki_name})
    req.cursor.execute("SELECT id from wikis where id=%(wiki_id)s", {'wiki_id': wiki_id})
    result = req.cursor.fetchone()
    req.cursor.execute("SELECT max(id) FROM wikis")
    new_wiki_id = req.cursor.fetchone()[0] + 1
    if result:
       # there is a wiki that exists with this id
       # lets move this wiki to an unused id
       exisiting_wiki_id = wiki_id
       if not has_wiki_name:
           req.cursor.execute("UPDATE wikis SET id=%(new_id)s WHERE id=%(old_id)s",
               {'new_id': new_wiki_id, 'old_id': exisiting_wiki_id}, isWrite=True)
       for table in tables_with_wiki_id:
           if not has_wiki_name:
               req.cursor.execute("UPDATE " + table + " SET wiki_id=%(new_id)s WHERE wiki_id=%(old_id)s",
	               {'new_id': new_wiki_id, 'old_id': exisiting_wiki_id}, isWrite=True)
           else:
               # we clear out the old test wiki's data
               req.cursor.execute("DELETE from " + table + " where wiki_id=%(old_id)s",
	               {'new_id': new_wiki_id, 'old_id': exisiting_wiki_id}, isWrite=True)
       

def tuple_format(l):
    t = '('
    i = 0
    d = {}
    for item in l[:-1]:
        t = t + '%' + '(%s)s,' % i
        if type(item) == buffer:
            item = wikidb.dbapi.Binary(item)
        d[str(i)] = item
        i += 1

    item = l[i]
    if type(item) == buffer:
        item = wikidb.dbapi.Binary(item)
    d[str(i)] = item
    t = t + '%' + '(%s)s' % i
    t += ')'
    return t, d

def get_db(wiki_dict):
    from Sycamore import wikidb
    db_name = wiki_dict['db_name']
    db_user = wiki_dict['db_user']
    db_user_password = wiki_dict['db_user_password']
    d = {}
    if config.db_host:
      d['host'] = config.db_host
    if db_user:
        d['user'] = db_user
    if db_name:
        if config.db_type == 'mysql':
            d['db'] = db_name
        elif config.db_type == 'postgres':
            d['database'] = db_name
    if db_user_password:
        if config.db_type == 'postgres':
            d['password'] = db_user_password
        elif config.db_type == 'mysql':
            d['passwd'] = db_user_password
    if config.db_socket:
        d['unix_socket'] = config.db_socket
    if config.db_type == 'mysql':
        d['init_command'] = 'SET NAMES utf8'
        d['charset'] = 'utf8'

    db = wikidb.dbapi.connect(**d)
    return db

req = request.RequestDummy()

for wiki_dict in wikis_to_merge:
    wiki_db = get_db(wiki_dict)
    wiki_cursor = wiki_db.cursor()
    wiki_dict['db'] = wiki_db
    wiki_dict['cursor'] = wiki_cursor

users = find_canonical_users(wikis_to_merge, req)

req.cursor.execute("SELECT max(uid) from events")
result = req.cursor.fetchone()
if result:
  max_uid_events = result[0] or 1

for wiki_dict in wikis_to_merge:
    wiki_cursor = wiki_dict['cursor']
    wiki_cursor.execute("SELECT max(uid) from events;")
    result = wiki_cursor.fetchone()
    if result and result[0]:
       max_uid_events = max(max_uid_events, result[0])

for wiki_dict in wikis_to_merge:
    wiki_cursor = wiki_dict['cursor']
    # if the wiki's id is already in the main hub
    # then we move the existing wiki to a new id
    move_potential_wiki_id_conflicts(wiki_cursor, req)
    move_potential_uid_conflicts(wiki_cursor, req)
    
    for table, columns in tables:
        if table == 'users':
            continue

	columns = ','.join(columns)
	print 'merging table', table
        wiki_cursor.execute("SELECT %s from %s" % (columns, table))
        try:
            result = wiki_cursor.fetchone()
            while result:
                t, d = tuple_format(result)
                req.cursor.execute("INSERT into %s (%s) VALUES %s" % (table, columns, t), d, isWrite=True)
                result = wiki_cursor.fetchone()
	except ValueError:
            print "ValueError on", table, "at", wiki_dict['db_name']
            raise Exception

set_incremented_values(req)

clear_user_sessions(req)

req.db_disconnect()

print "Done with merge!"
