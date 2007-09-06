import sys, cStringIO, os, shutil, re
from copy import copy
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])

from Sycamore import wikiutil, config, request, caching, wikidb, maintenance, buildDB, wikiacl, maintenance
from Sycamore.Page import Page

# things you might want to change
# ignore this: sc: 5, dwiki: 2, roc:3, pgh:4, proj:6, ant:7, chico:8
wiki_id = 1
wiki_name = config.wiki_name
d = {"wiki_id": wiki_id, "wiki_name": wiki_name}
maps_start = 0
events_start = 0

# don't change these
maps_start_local = None
events_start_local = None

def new_static_data():
    if not os.path.exists(os.path.join(config.data_dir, 'audio')):
        shutil.copytree('audio', os.path.join(confing.data_dir, 'audio'))
    current_dirname = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(config.data_dir, 'audio')):
      shutil.copytree(os.path.join(current-dirname, 'audio'), os.path.join(config.data_dir, 'audio'))

def rebuild_all_caches():
    req = request.RequestDummy()
    wiki_list = wikiutil.getWikiList(req)
    for wiki_name in wiki_list:
       req.switch_wiki(wiki_name)
       plist = wikiutil.getPageList(req)
       maintenance.buildCaches(wiki_name, plist, doprint=True)
    req.db_disconnect()

def convert_user_wiki_info(request):
    from Sycamore import user
    for id in user.getUserList(request.cursor):
        theuser = user.User(request, id=id)
        request.cursor.execute("SELECT created_count, edit_count, last_page_edited, last_edit_date from users where id=%(id)s", {'id': theuser.id})
        result = request.cursor.fetchone()
        if result:
            created_count, edit_count, last_page_edited, last_edit_date = result
            wiki_info = theuser.getWikiInfo()
            wiki_info.created_count = created_count
            wiki_info.edit_count = edit_count
            wiki_info.last_page_edited = last_page_edited
            wiki_info.last_edit_date = last_edit_date
            theuser.setWikiInfo(wiki_info)

#def _fix_user_text(text, request):
#    from Sycamore import user
#    fixed = []
#    offset = 0
#    for match in re.finditer('\["(?P<pagename>[^\n"]+)"(?P<alt>[^\n]*?)\]', text):
#        pagename = match.group('pagename')
#        alt = match.group('alt')
#        isuser = user.User(request, name=pagename.lower())
#        if isuser.valid:
#            if not alt.strip():
#                alt = " %s" % pagename
#            text = text[:match.start('pagename')+offset] + config.user_page_prefix + pagename + text[match.end('pagename')+offset:match.start('alt')+offset] + alt + text[match.end('alt')+offset:]
#            offset += len(config.user_page_prefix) + len(alt)
#    return text


#def convert_user_links(request):
#    """
#    Takes the page text from all pages and converts what appear to be links to old-style user pages to new links.
#    """
#    from Sycamore import user
#                    
#    for wikiname in wikiutil.getWikiList(request):
#        request.switch_wiki(wikiname)
#        pagelist = wikiutil.getPageList(request, objects=True)
#        num_pages = len(pagelist)
#        n = 0
#        for page in pagelist:
#            text = page.get_raw_body() 
#            text = _fix_user_text(text, request)
#            d = {'newtext': text, 'pagename': page.page_name, 'wiki_id': request.config.wiki_id, 'mtime': page.mtime()}
#            request.cursor.execute("UPDATE curPages set text=%(newtext)s where name=%(pagename)s and wiki_id=%(wiki_id)s", d, isWrite=True)
#            request.cursor.execute("UPDATE allPages set text=%(newtext)s where name=%(pagename)s and editTime=%(mtime)s and wiki_id=%(wiki_id)s", d, isWrite=True)
#            n += 1 
#            print '  ', ((n*1.0)/num_pages)*100, 'percent done'

def _get_user_pages(request):
    from Sycamore import user
    pages = []
    for page in wikiutil.getPageList(request, objects=True):
        if user.User(request, name=page.page_name).valid:
            # it's a user page 
            pages.append(page)
    return pages 

def _user_page_move(request, d):
    request.cursor.execute("UPDATE curPages set name=%(new_name)s, propercased_name=%(new_propercased_name)s where name=%(old_pagename)s and wiki_id=%(wiki_id)s", d, isWrite=True)
    request.cursor.execute("SELECT name, editTime, propercased_name from allPages where name=%(old_pagename)s and wiki_id=%(wiki_id)s", d)
    result = request.cursor.fetchall()
    if result:
        # we want to preserve the subtle differences in old page proper names, hense the iteration here
        for name, editTime, propercased_name in result:
            d['new_propercased_name'] = config.user_page_prefix + propercased_name
            d['editTime'] = editTime
            request.cursor.execute("UPDATE allPages set name=%(new_name)s, propercased_name=%(new_propercased_name)s where name=%(old_pagename)s and editTime=%(editTime)s and wiki_id=%(wiki_id)s", d, isWrite=True)

    # Tables that require we only change the basic pagename
    request.cursor.execute("UPDATE imageInfo set attached_to_pagename=%(new_name)s where attached_to_pagename=%(old_pagename)s and wiki_id=%(wiki_id)s", d, isWrite=True)
    request.cursor.execute("UPDATE oldImageInfo set attached_to_pagename=%(new_name)s where attached_to_pagename=%(old_pagename)s and wiki_id=%(wiki_id)s", d, isWrite=True)
    request.cursor.execute("UPDATE pageAcls set pagename=%(new_name)s where pagename=%(old_pagename)s and wiki_id=%(wiki_id)s", d, isWrite=True)
    request.cursor.execute("UPDATE userFavorites set page=%(new_name)s where page=%(old_pagename)s and wiki_name=%(wiki_name)s", d, isWrite=True)

    # We need to iterate in these cases so that we preserve the old proper name
    request.cursor.execute("SELECT name, attached_to_pagename, attached_to_pagename_propercased from files where attached_to_pagename=%(old_pagename)s and wiki_id=%(wiki_id)s", d)
    result = request.cursor.fetchall()
    if result:
        # we want to preserve the subtle differences in old page proper names, hense the iteration here
        for name, attached_to_pagename, attached_to_pagename_propercased in result:
            d['new_propercased_name'] = config.user_page_prefix + attached_to_pagename_propercased
            request.cursor.execute("UPDATE files set attached_to_pagename=%(new_name)s, attached_to_pagename_propercased=%(new_propercased_name)s where attached_to_pagename=%(old_pagename)s and wiki_id=%(wiki_id)s", d, isWrite=True)

    request.cursor.execute("SELECT name, attached_to_pagename, attached_to_pagename_propercased, uploaded_time from oldFiles where attached_to_pagename=%(old_pagename)s and wiki_id=%(wiki_id)s", d)
    result = request.cursor.fetchall()
    if result:
        # we want to preserve the subtle differences in old page proper names, hense the iteration here
        for name, attached_to_pagename, attached_to_pagename_propercased, uploaded_time in result:
            d['new_propercased_name'] = config.user_page_prefix + attached_to_pagename_propercased
            d['uploaded_time'] = uploaded_time
            request.cursor.execute("UPDATE oldFiles set attached_to_pagename=%(new_name)s, attached_to_pagename_propercased=%(new_propercased_name)s where attached_to_pagename=%(old_pagename)s and uploaded_time=%(uploaded_time)s and wiki_id=%(wiki_id)s", d, isWrite=True)

    request.cursor.execute("SELECT pagename, pagename_propercased, x, y from mapPoints where pagename=%(old_pagename)s and wiki_id=%(wiki_id)s", d)
    result = request.cursor.fetchall()
    if result:
        # we want to preserve the subtle differences in old page proper names, hense the iteration here
        for pagename, pagename_propercased, x, y in result:
            d['new_propercased_name'] = config.user_page_prefix + pagename_propercased
            d['x'] = x
            d['y'] = y
            request.cursor.execute("UPDATE mapPoints set pagename=%(new_name)s, pagename_propercased=%(new_propercased_name)s where pagename=%(old_pagename)s and x=%(x)s and y=%(y)s and wiki_id=%(wiki_id)s", d, isWrite=True)

    request.cursor.execute("SELECT pagename, pagename_propercased, x, y, deleted_time from oldMapPoints where pagename=%(old_pagename)s and wiki_id=%(wiki_id)s", d)
    result = request.cursor.fetchall()
    if result:
        # we want to preserve the subtle differences in old page proper names, hense the iteration here
        for pagename, pagename_propercased, x, y, deleted_time in result:
            d['new_propercased_name'] = config.user_page_prefix + pagename_propercased
            d['x'] = x
            d['y'] = y
            d['deleted_time'] = deleted_time
            request.cursor.execute("UPDATE oldMapPoints set pagename=%(new_name)s, pagename_propercased=%(new_propercased_name)s where pagename=%(old_pagename)s and x=%(x)s and y=%(y)s and deleted_time=%(deleted_time)s and wiki_id=%(wiki_id)s", d, isWrite=True)

def _user_page_redirect(request, d):
    d['redirect_text'] = "#redirect %s" % d['new_propercased_name']
    print d['redirect_text']
    request.cursor.execute("INSERT into curPages (name, propercased_name, text, editTime, wiki_id) values (%(old_pagename)s, %(old_propercased_name)s, %(redirect_text)s, %(latest_ed_time)s, %(wiki_id)s)", d, isWrite=True)
    request.cursor.execute("INSERT into allPages (name, propercased_name, text, editTime, editType, wiki_id) values (%(old_pagename)s, %(old_propercased_name)s, %(redirect_text)s, %(latest_ed_time)s, 'SAVE', %(wiki_id)s)", d, isWrite=True)


def rename_old_user_pages(request):
    from Sycamore import user
    for wikiname in wikiutil.getWikiList(request):
        request.switch_wiki(wikiname)
        user_pages = _get_user_pages(request) 
        num_user_pages = len(user_pages)
        n = 0
        for page in user_pages:
            new_user_pagename = config.user_page_prefix + page.proper_name()
            new_user_page = Page(new_user_pagename, request)
            if new_user_page.exists():
                # something crazzzzy is going on
                continue 
            old_pagename_propercased = page.proper_name()
            d = {'new_name': new_user_pagename.lower(), 'new_propercased_name': new_user_pagename,
                'old_pagename': page.page_name, 'wiki_id': request.config.wiki_id,
                'wiki_name': request.config.wiki_name, 'latest_ed_time': page.mtime(),
                'old_propercased_name': page.proper_name()}

            print page.page_name, '->', new_user_pagename
            _user_page_move(request, copy(d))
            _user_page_redirect(request, d)
            n += 1
            #print "  ", ((n*1.0)/num_user_pages)*100, "user pages renamed"


def fix_events(request):
    global events_start_local
    request.cursor.execute("ALTER TABLE events ADD COLUMN wiki_id int;", isWrite=True)
    request.cursor.execute("UPDATE events set wiki_id=%(wiki_id)s", d, isWrite=True)
    max = None
    request.cursor.execute("SELECT max(uid) from events")
    result = request.cursor.fetchone()
    if result:
    	max = result[0] 
    if max is None:
    	max = 1
    events_start_local = max
 
    if config.db_type == 'postgres':
       request.cursor.execute("CREATE sequence events_seq start %s increment 1;" % max, isWrite=True) 
       request.cursor.execute("DROP INDEX events_event_time;", isWrite=True)
    elif config.db_type == 'mysql':
       request.cursor.execute("ALTER TABLE events change uid uid int not null AUTO_INCREMENT;", isWrite=True)
       request.cursor.execute("ALTER TABLE events AUTO_INCREMENT = %s;" % max, isWrite=True)
       request.cursor.execute("ALTER TABLE events DROP INDEX events_event_time;", isWrite=True)

    request.cursor.execute("CREATE INDEX events_event_time on events (event_time, wiki_id);", isWrite=True)
    request.cursor.execute("CREATE INDEX events_posted_time_wiki_id on events (posted_time, wiki_id);", isWrite=True) # global events

    # re-insert events so that they start at the events_start uid
    request.cursor.execute("SELECT uid, event_time, posted_by, text, location, event_name, posted_by_ip, posted_time from events where wiki_id=%(wiki_id)s", d)
    results = request.cursor.fetchall()
    if results: 
      request.cursor.execute("DELETE from events where wiki_id=%(wiki_id)s", d, isWrite=True)
      for result in results: 
        result_dict = {'uid': result[0] + events_start, 'event_time': result[1], 'posted_by': result[2], 'text': result[3], 'location': result[4], 'event_name': result[5], 'posted_by_ip': result[6], 'posted_time': result[7], 'wiki_id': wiki_id}
        request.cursor.execute("INSERT into events (uid, event_time, posted_by, text, location, event_name, posted_by_ip, posted_time, wiki_id) values (%(uid)s, %(event_time)s, %(posted_by)s, %(text)s, %(location)s, %(event_name)s, %(posted_by_ip)s, %(posted_time)s, %(wiki_id)s)", result_dict, isWrite=True)
        
def fix_mapPoints(request):
    global maps_start_local
    if wiki_name is not 'rochester':
        request.cursor.execute("ALTER TABLE mapPoints ADD COLUMN address varchar(255);", isWrite=True)
    request.cursor.execute("ALTER TABLE mapPoints ADD COLUMN wiki_id int;", isWrite=True)
    request.cursor.execute("UPDATE mapPoints set wiki_id=%(wiki_id)s", d, isWrite=True)
    max = None
    request.cursor.execute("SELECT max(id) from mapPoints")
    result = request.cursor.fetchone()
    if result:
    	max = result[0] 
    if max is None:
    	max = 1
    maps_start_local = max
 
    if config.db_type == 'postgres':
       request.cursor.execute("CREATE sequence mapPoints_seq start %s increment 1;" % max, isWrite=True) 
    elif config.db_type == 'mysql':
       request.cursor.execute("ALTER TABLE mapPoints change id id int not null AUTO_INCREMENT;", isWrite=True)
       request.cursor.execute("ALTER TABLE mapPoints AUTO_INCREMENT = %s;" % max, isWrite=True)

    request.cursor.execute("""CREATE INDEX mapPoints_pagename_wiki_id on mapPoints (pagename, wiki_id);""", isWrite=True)
    request.cursor.execute("""CREATE INDEX mapPoints_x on mapPoints (x);""", isWrite=True)
    request.cursor.execute("""CREATE INDEX mapPoints_y on mapPoints (y);""", isWrite=True)
    request.cursor.execute("""CREATE INDEX mapPoints_wiki on mapPoints (wiki_id);""", isWrite=True)
    request.cursor.execute("""CREATE INDEX mapPoints_created_time_wiki_id on mapPoints (created_time, wiki_id);""", isWrite=True)  # local rc
    request.cursor.execute("""CREATE INDEX mapPoints_address on mapPoints (address);""", isWrite=True)

    # re-insert map points so that they start at the maps_start uid
    request.cursor.execute("SELECT pagename, x, y, created_time, created_by, created_by_ip, id, pagename_propercased, address from mapPoints where wiki_id=%(wiki_id)s", d)
    results = request.cursor.fetchall()
    if results: 
      request.cursor.execute("DELETE from mapPoints where wiki_id=%(wiki_id)s", d, isWrite=True)
      i = 0
      for result in results: 
      	if wiki_name == 'rochester':
	    # rocwiki has the same id for all mapPoints..huh
            i += 1
        result_dict = {'pagename': result[0], 'x': result[1], 'y': result[2], 'created_time': result[3], 'created_by': result[4], 'created_by_ip': result[5], 'id': result[6] + maps_start + i, 'pagename_propercased': result[7], 'address': result[8], 'wiki_id': wiki_id}
        request.cursor.execute("INSERT into mapPoints (pagename, x, y, created_time, created_by, created_by_ip, id, pagename_propercased, address, wiki_id) values (%(pagename)s, %(x)s, %(y)s, %(created_time)s, %(created_by)s, %(created_by_ip)s, %(id)s, %(pagename_propercased)s, %(address)s, %(wiki_id)s)", result_dict, isWrite=True)


req = request.RequestDummy(process_config=False)

req.cursor.execute("ALTER TABLE curPages ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE curPages set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE curPages DROP CONSTRAINT curpages_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE curPages DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE curPages ADD PRIMARY KEY (name, wiki_id);", isWrite=True)

req.cursor.execute("ALTER TABLE allPages ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE allPages set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE allPages DROP CONSTRAINT allpages_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE allPages DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE allPages ADD PRIMARY KEY (name, editTime, wiki_id);", isWrite=True)
req.cursor.execute("CREATE INDEX editTime_wiki_id on allPages (editTime, wiki_id);", isWrite=True)

req.cursor.execute("ALTER TABLE users ADD COLUMN last_wiki_edited int;", isWrite=True)
if config.db_type == 'mysql':
    req.cursor.execute("ALTER TABLE users CHANGE COLUMN tz_offset TO tz varchar(50);", isWrite=True)
else:
    req.cursor.execute("ALTER TABLE users RENAME COLUMN tz_offset TO tz;", isWrite=True)
req.cursor.execute("ALTER TABLE users ALTER COLUMN tz TYPE varchar(50);", isWrite=True)
req.cursor.execute("UPDATE users SET tz=%(config_tz)s;", {'config_tz': req.config.tz}, isWrite=True)
req.cursor.execute("ALTER TABLE users ADD COLUMN wiki_for_userpage varchar(100);", isWrite=True)
req.cursor.execute("ALTER TABLE users ADD CHECK (disabled IN ('0', '1'));", isWrite=True)
req.cursor.execute("ALTER TABLE users ADD CHECK (remember_me IN ('0', '1'));", isWrite=True)
req.cursor.execute("ALTER TABLE users ADD CHECK (rc_showcomments IN ('0', '1'));", isWrite=True)
req.cursor.execute("ALTER TABLE users ADD COLUMN rc_group_by_wiki boolean default false;", isWrite=True)

req.cursor.execute("ALTER TABLE userFavorites ADD COLUMN wiki_name varchar(100);", isWrite=True)
req.cursor.execute("UPDATE userFavorites set wiki_name=%(wiki_name)s", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE userFavorites DROP CONSTRAINT userfavorites_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE userFavorites DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE userFavorites ADD PRIMARY KEY (username, page, wiki_name);", isWrite=True)
req.cursor.execute("CREATE INDEX userfavorites_username on userFavorites (username);", isWrite=True)
req.cursor.execute("ALTER TABLE links ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE links set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE links DROP CONSTRAINT links_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE links DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE links ADD PRIMARY KEY (source_pagename, destination_pagename, wiki_id);", isWrite=True)
req.cursor.execute("CREATE INDEX links_source_pagename_wiki_id on links (source_pagename, wiki_id);", isWrite=True)
req.cursor.execute("CREATE INDEX links_destination_pagename_wiki_id on links (destination_pagename, wiki_id);", isWrite=True)


req.cursor.execute("ALTER TABLE files ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE files set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE files DROP CONSTRAINT files_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE files DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE files ADD PRIMARY KEY (name, attached_to_pagename, wiki_id);", isWrite=True)
req.cursor.execute("CREATE INDEX files_uploaded_time_wiki_id on files (uploaded_time, wiki_id);", isWrite=True) # local rc

req.cursor.execute("ALTER TABLE oldFiles ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE oldFiles set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE oldFiles DROP CONSTRAINT oldfiles_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE oldFiles DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE oldFiles ADD PRIMARY KEY (name, attached_to_pagename, uploaded_time, wiki_id);", isWrite=True)
req.cursor.execute("CREATE INDEX oldFiles_deleted_time_wiki_id on oldFiles (deleted_time, wiki_id);", isWrite=True)   # local rc

req.cursor.execute("ALTER TABLE thumbnails ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE thumbnails set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE thumbnails DROP CONSTRAINT thumbnails_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE thumbnails DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE thumbnails ADD PRIMARY KEY (name, attached_to_pagename, wiki_id);", isWrite=True)

req.cursor.execute("ALTER TABLE imageInfo ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE imageInfo set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE imageInfo DROP CONSTRAINT imageinfo_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE imageInfo DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE imageInfo ADD PRIMARY KEY (name, attached_to_pagename, wiki_id);", isWrite=True)

req.cursor.execute("ALTER TABLE oldImageInfo ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE oldImageInfo set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE oldImageInfo DROP CONSTRAINT oldimageinfo_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE oldImageInfo DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE oldImageInfo ADD PRIMARY KEY (name, attached_to_pagename, uploaded_time, wiki_id);", isWrite=True)

req.cursor.execute("ALTER TABLE imageCaptions ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE imageCaptions set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE imageCaptions DROP CONSTRAINT imagecaptions_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE imageCaptions DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE imageCaptions ADD PRIMARY KEY (image_name, attached_to_pagename, linked_from_pagename, wiki_id);", isWrite=True)

req.cursor.execute("ALTER TABLE mapCategoryDefinitions ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE mapCategoryDefinitions set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE mapCategoryDefinitions DROP CONSTRAINT mapcategorydefinitions_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE mapCategoryDefinitions DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE mapCategoryDefinitions ADD PRIMARY KEY (id, wiki_id);", isWrite=True)


req.cursor.execute("ALTER TABLE oldMapPoints ADD COLUMN address varchar(255);", isWrite=True)
req.cursor.execute("ALTER TABLE oldMapPoints ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE oldMapPoints set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE oldMapPoints DROP CONSTRAINT oldmappoints_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE oldMapPoints DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE oldMapPoints ADD PRIMARY KEY (pagename, x, y, deleted_time, wiki_id);", isWrite=True)
req.cursor.execute("CREATE INDEX oldMapPoints_deleted_time_wiki_id on oldMapPoints (deleted_time, wiki_id);", isWrite=True)  # local rc
req.cursor.execute("CREATE INDEX oldMapPoints_created_time_wiki_id on oldMapPoints (created_time, wiki_id);", isWrite=True)  # local rc

req.cursor.execute("ALTER TABLE mapPointCategories ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE mapPointCategories set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE mapPointCategories DROP CONSTRAINT mappointcategories_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE mapPointCategories DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE mapPointCategories ADD PRIMARY KEY (pagename, x, y, id, wiki_id);", isWrite=True)

req.cursor.execute("ALTER TABLE oldMapPointCategories ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE oldMapPointCategories set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE oldMapPointCategories DROP CONSTRAINT oldmappointcategories_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE oldMapPointCategories DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE oldMapPointCategories ADD PRIMARY KEY (pagename, x, y, id, deleted_time, wiki_id);", isWrite=True)

req.cursor.execute("ALTER TABLE pageDependencies ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE pageDependencies set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE pageDependencies DROP CONSTRAINT pagedependencies_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE pageDependencies DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE pageDependencies ADD PRIMARY KEY (page_that_depends, source_page, wiki_id);", isWrite=True)

req.cursor.execute("ALTER TABLE metadata ADD COLUMN wiki_id int;", isWrite=True)
req.cursor.execute("UPDATE metadata set wiki_id=%(wiki_id)s;", d, isWrite=True)
if config.db_type == 'postgres':
  req.cursor.execute("ALTER TABLE metadata DROP CONSTRAINT metadata_pkey;", isWrite=True)
elif config.db_type == 'mysql':
  req.cursor.execute("ALTER TABLE metadata DROP PRIMARY KEY;", isWrite=True)
req.cursor.execute("ALTER TABLE metadata ADD PRIMARY KEY (pagename, type, name, wiki_id);", isWrite=True)

if config.db_type == 'mysql':
 req.cursor.execute("""create table wikis
  (
    id int not null AUTO_INCREMENT,
    name varchar(100) unique not null,
    domain varchar(64),
    is_disabled BOOLEAN,
    sitename varchar(100),
    other_settings mediumblob,
    primary key (id)
  ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
 req.cursor.execute("ALTER TABLE wikis AUTO_INCREMENT = 1;", isWrite=True)
elif config.db_type == 'postgres':
  req.cursor.execute("""create table wikis
  (
     id int not null,
     name varchar(100) unique not null,
     domain varchar(64),
     is_disabled boolean,
     sitename varchar(100),
     other_settings bytea,
     primary key (id)
  )""", isWrite=True)
  req.cursor.execute("CREATE sequence wikis_seq start 1 increment 1;", isWrite=True)

req.cursor.execute("CREATE INDEX wikis_name on wikis (name);", isWrite=True)
req.cursor.execute("CREATE INDEX wikis_domain on wikis (domain);", isWrite=True)

if config.db_type == 'mysql':
  req.cursor.execute("""create table userWikiInfo
  (
    user_name varchar(100) not null,
    wiki_id int,
    first_edit_date double,
    created_count int default 0, 
    edit_count int default 0,
    file_count int default 0,
    last_page_edited varchar(100), 
    last_edit_date double,
    rc_bookmark double,
    primary key (user_name, wiki_id)
  ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
elif config.db_type == 'postgres':
  req.cursor.execute("""create table userWikiInfo
  (
     user_name varchar(100) not null,
     wiki_id int,
     first_edit_date double precision,
     created_count int default 0,
     edit_count int default 0,
     file_count int default 0,
     last_page_edited varchar(100),
     last_edit_date double precision,
     rc_bookmark double precision,
     primary key (user_name, wiki_id)
  )""", isWrite=True)

if config.db_type == 'mysql':
  req.cursor.execute("""create table pageAcls
  (
    pagename varchar(100) not null,
    groupname varchar(100) not null,
    wiki_id int,
    may_read BOOLEAN,
    may_edit BOOLEAN,
    may_delete BOOLEAN,
    may_admin BOOLEAN, 
    primary key (pagename, groupname, wiki_id)
  ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
elif config.db_type == 'postgres':
  req.cursor.execute("""create table pageAcls
  (
     pagename varchar(100) not null,
     groupname varchar(100) not null,
     wiki_id int,
     may_read boolean, 
     may_edit boolean,
     may_delete boolean,
     may_admin boolean,
     primary key (pagename, groupname, wiki_id)
  )""", isWrite=True)

req.cursor.execute("CREATE INDEX pageAcls_pagename_wiki on pageAcls (pagename, wiki_id);", isWrite=True)

if config.db_type == 'mysql':
  req.cursor.execute("""create table userGroups
  (
    username varchar(100) not null,
    groupname varchar(100) not null,
    wiki_id int,
    primary key (username, groupname, wiki_id)
  ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
elif config.db_type == 'postgres':
  req.cursor.execute("""create table userGroups
  (
     username varchar(100) not null,
     groupname varchar(100) not null,
     wiki_id int,
     primary key (username, groupname, wiki_id)
  )""", isWrite=True)

req.cursor.execute("CREATE INDEX user_groups_group_wiki on userGroups (groupname, wiki_id);", isWrite=True)

if config.db_type == 'mysql':
  req.cursor.execute("""create table userGroupsIPs
  (
    ip char(16) not null,
    groupname varchar(100) not null,
    wiki_id int,
    primary key (ip, groupname, wiki_id)
  ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
elif config.db_type == 'postgres':
  req.cursor.execute("""create table userGroupsIPs
  (
     ip inet not null,
     groupname varchar(100) not null,
     wiki_id int,
     primary key (ip, groupname, wiki_id)
  )""", isWrite=True)

req.cursor.execute("CREATE INDEX user_groups_ip_ips on userGroupsIPs (groupname, wiki_id);", isWrite=True)

fix_events(req)
fix_mapPoints(req)

req.cursor.execute("DROP VIEW eventChanges;", isWrite=True)
req.cursor.execute("DROP VIEW deletedFileChanges;", isWrite=True)
req.cursor.execute("DROP VIEW oldFileChanges;", isWrite=True)
req.cursor.execute("DROP VIEW currentFileChanges;", isWrite=True)
req.cursor.execute("DROP VIEW pageChanges;", isWrite=True)
req.cursor.execute("DROP VIEW currentMapChanges;", isWrite=True)
req.cursor.execute("DROP VIEW oldMapChanges;", isWrite=True)
req.cursor.execute("DROP VIEW deletedMapChanges;", isWrite=True)

if config.db_type == 'mysql':
  req.cursor.execute("""create table lostPasswords
  (
    uid char(20) not null,
    code varchar(255),
    written_time double,
    primary key (uid, code, written_time)
  ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
elif config.db_type == 'postgres':
  req.cursor.execute("""create table lostPasswords
  (
    uid char(20) not null,
    code varchar(255),
    written_time double precision,
    primary key (uid, code, written_time)
  )""", isWrite=True)

req.cursor.execute("CREATE INDEX lostpasswords_uid on lostPasswords (uid);", isWrite=True)
req.cursor.execute("CREATE INDEX lostpasswords_written_time on lostPasswords (written_time);", isWrite=True)

if config.db_type == 'mysql':
    reqcursor.execute("""create table wikisPending
    (
      wiki_name varchar(100) not null,
      code varchar(255) not null,
      written_time double not null,
      primary key (wiki_name, code, written_time)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
elif config.db_type == 'postgres':
  req.cursor.execute("""create table wikisPending
  (
    wiki_name varchar(100) not null,
    code varchar(255) not null,
    written_time double precision not null,
    primary key (wiki_name, code, written_time)
  )""", isWrite=True)

req.cursor.execute("CREATE INDEX wikispending_written_time on wikisPending (written_time);", isWrite=True)

if config.db_type == 'mysql':
    req.cursor.execute("""create table captchas
    (
      id char(33) primary key,
      secret varchar(100) not null,
      human_readable_secret mediumblob,
      written_time double
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
elif config.db_type == 'postgres':
    req.cursor.execute("""create table captchas
    (
      id char(33) primary key,
      secret varchar(100) not null,
      human_readable_secret bytea,
      written_time double precision
    )""", isWrite=True)

req.cursor.execute("CREATE INDEX captchas_written_time on captchas (written_time);", isWrite=True)

if config.db_type == 'mysql':
  req.cursor.execute("""create table userWatchedWikis
  (
  username varchar(100) not null,
  wiki_name varchar(100) not null,
  primary key (username, wiki_name)
  ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
elif config.db_type == 'postgres':
  req.cursor.execute("""create table userWatchedWikis
  (
  username varchar(100) not null,
  wiki_name varchar(100) not null,
  primary key (username, wiki_name)
  );""", isWrite=True)

req.cursor.execute("CREATE INDEX userWatchedWikis_username on userWatchedWikis (username);", isWrite=True)
req.cursor.execute("CREATE INDEX userWatchedWikis_wiki_name on userWatchedWikis (wiki_name);", isWrite=True)

buildDB.create_views(req.cursor)
buildDB.create_config(req, wiki_id=wiki_id)

req.db_disconnect()

new_static_data()

req = request.RequestDummy()
print "---------"
#print 'converting user links....'
#print "---------"
#convert_user_links(req)
print 'renaming user pages'
print "---------"
rename_old_user_pages(req)
print "---------"
print 'converting user wiki info'
convert_user_wiki_info(req)
req.db_disconnect()

#rebuild_all_caches()

print "Done with convert!"
print "---------"
print "maps start: %s, events start: %s (for reference)" % (maps_start_local, events_start_local)
