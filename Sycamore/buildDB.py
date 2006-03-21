# Build a wiki database from scratch.  You should run this the FIRST TIME you install your wiki.
import sys, os, shutil
import __init__ # woo hackmagic
from Sycamore import wikidb, config

basic_pages = {}
# We do the basic database population here
basic_pages["User Preferences"] =  """#acl AdminGroup:admin,read,write,delete,revert All:read
[[UserPreferences]]

= First time =
/!\ Your email is needed for you to be able to recover lost login data.

If you click on '''[[GetText(Create Profile)]]''', a user profile will be created for you and you will be logged in immediately.

= Forgot password? =
If you forgot your password, attempt to log in via the login box in the upper right hand corner of the screen and you will be given further instruction."""

basic_pages["Recent Changes"] = """#acl AdminGroup:admin,read,write,delete,revert All:read
||<bgcolor='#ffffaa'>'''TIP''':  [[RandomQuote(Quick Wiki Tips)]]||
[[BR]]
[[RecentChanges]]
[[BR]]

||<:> [[Icon(diffrc)]] || marks older pages that have at least one backup version stored (click for an author ''diff''erence)||
||<:> [[Icon(updated)]] || marks pages edited since you last pressed 'clear observed changes' (click to see differences since you cleared)||
||<:> [[Icon(new)]] || marks new pages||
----
This page contains a list of recent changes in this wiki of '''[[PageCount]] pages''' (more system information on ["System Info"] -- there are also ["User Statistics"])."""

basic_pages["Front Page"] = """Edit me..This is the Front Page!"""

basic_pages["Orphaned Pages"] = """A list of pages no other page links to.  You cannot find these pages unless you ''search'' for them -- so let's link them from someplace!

The dual to this page is ["Outgoing Links"] -- a list of pages based upon the number of links ''leaving'' each page.

[[OrphanedPages]]"""

basic_pages["Outgoing Links"] = """This is a list of all pages based upon the number of links on each page (links from the page to other pages). Pages with few links are 'dead ends': you have few choices once you're there!  (Note: redirect pages are filtered from this list.) The dual of this page is ["Orphaned Pages"] -- pages with no links to them.

[[OutgoingLinks]]"""

basic_pages["Wanted Pages"] = """We call a page "wanted" when there are links made to it but the page does not yet exist.  By creating a wanted page you're adding something that others had probably desired to see on the wiki.

This list is only advisory: '''just because a page is listed here does not make it necessary.''' Look carefully at the pages that link to it and use your judgement.

[[WantedPages]]"""

basic_pages["Title Index"] = """This is an index of all pages in the Wiki.  

See also ["Site Organization"] for other ways to check out pages in the wiki/keep it well organized.

----
[[TitleIndex]]"""

basic_pages["Bookmarks"] = """#acl AdminGroup:read,write,delete,revert,admin All:read
[[Bookmarks]]

----
'''Bolded''' items have been modified since you last viewed them.  Clicking ''diff'' will show you the differences between the version of the page you last saw and the current version, or will show the most recent difference (if only one change has been made since you last viewed the page)."""

basic_pages["System Pages Group"] = """ * Front Page
 * People
 * Bookmarks
 * Recent Changes
 * User Statistics
 * User Preferences
 * Map"""

basic_pages["User Statistics"] = """[[Stats]]

There are '''[[UserCount]]''' registered accounts on the wiki.

----
If you'd like personalized statistics on your page, simply insert the line {{{[[Stats(YourName)]]}}} into your page."""

def init_db(cursor):
  if config.db_type == 'postgres':
    cursor.execute("CREATE FUNCTION UNIX_TIMESTAMP(timestamp) RETURNS integer AS 'SELECT date_part(''epoch'', $1)::int4 AS result' language 'sql';")

def create_tables(cursor):
 print "creating tables.."
 if config.db_type == 'mysql':
   cursor.execute("""create table curPages
     (
     name varchar(100) primary key,
     text mediumtext,
     cachedText mediumblob,
     editTime double,
     cachedTime double,
     userEdited char(20)
     ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table curPages
     (
     name varchar(100) primary key,
     text text,
     cachedText bytea,
     editTime double precision,
     cachedTime double precision,
     userEdited char(20)
     );""")

 cursor.execute("CREATE INDEX curPages_userEdited on curPages (userEdited);")
 if config.db_type == 'mysql':
   cursor.execute("""create table allPages
     (
     name varchar(100),
     text mediumtext,
     editTime double,
     userEdited char(20),
     editType CHAR(30) CHECK (editType in ('SAVE','SAVENEW','ATTNEW','ATTDEL','RENAME','NEWEVENT','COMMENT_MACRO','SAVE/REVERT','DELETE', 'SAVEMAP')),
     comment varchar(81),
     userIP char(16),
     primary key(name, editTime)
     ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table allPages
     (
     name varchar(100),
     text text,
     editTime double precision,
     userEdited char(20),
     editType CHAR(30) CHECK (editType in ('SAVE','SAVENEW','ATTNEW','ATTDEL','RENAME','NEWEVENT','COMMENT_MACRO','SAVE/REVERT','DELETE', 'SAVEMAP')),
     comment varchar(81),
     userIP char(16),
     primary key (name, editTime)
     );""")

 cursor.execute("CREATE INDEX allPages_userEdited on allPages (userEdited);")
 cursor.execute("CREATE INDEX allPages_userIP on allPages (userIP);")

 if config.db_type == 'mysql':
   cursor.execute("""create table users
    (
    id char(20) primary key,
    name varchar(100),
    email varchar(255),
    enc_password varchar(255),
    language varchar(80),
    remember_me tinyint,
    css_url varchar(255),
    disabled tinyint,
    edit_cols smallint,
    edit_rows smallint,
    edit_on_doubleclick tinyint,
    theme_name varchar(40),
    last_saved double,
    join_date double,
    created_count int default 0,
    edit_count int default 0,
    file_count int default 0,
    last_page_edited varchar(255),
    last_edit_date double,
    rc_bookmark double,
    rc_showcomments tinyint default 1,
    tz_offset int
    ) type=InnoDB;""")
 elif config.db_type == 'postgres':
  cursor.execute("""create table users
    (
    id char(20) primary key,
    name varchar(100),
    email varchar(255),
    enc_password varchar(255),
    language varchar(80),
    remember_me smallint,
    css_url varchar(255),
    disabled smallint,
    edit_cols smallint,
    edit_rows smallint,
    edit_on_doubleclick smallint,
    theme_name varchar(40),
    last_saved double precision,
    join_date double precision,
    created_count int default 0,
    edit_count int default 0,
    file_count int default 0,
    last_page_edited varchar(255),
    last_edit_date double precision,
    rc_bookmark double precision,
    rc_showcomments smallint default 1,
    tz_offset int
    );""")

 cursor.execute("CREATE INDEX users_name on users (name);")

 if config.db_type == 'mysql':
   cursor.execute("""create table userFavorites
   (
   username varchar(100),
   page varchar(100),
   viewTime double,
   primary key (username, page)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table userFavorites
   (
   username varchar(100),
   page varchar(100),
   viewTime double precision,
   primary key (username, page)
   );""")

 if config.db_type == 'mysql':
   #This is throw-away data. User sessions aren't that important so we'll use a MyISAM table for speed
   cursor.execute("""create table userSessions
   (
   user_id char(20),
   session_id char(28),
   secret char(28),
   expire_time double,
   primary key (user_id, session_id)
   )type=MyISAM;""")
 elif config.db_type == 'postgres':
   #This is throw-away data. User sessions aren't that important so we'll use a MyISAM table for speed
   cursor.execute("""create table userSessions
   (
   user_id char(20),
   session_id char(28),
   secret char(28),
   expire_time double precision,
   primary key (user_id, session_id)
   );""")

 cursor.execute("CREATE INDEX userSessions_expire_time on userSessions (expire_time);")

 if config.db_type == 'mysql':
   cursor.execute("""create table links
   (
   source_pagename varchar(100),
   destination_pagename varchar(100),
   primary key (source_pagename, destination_pagename)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table links
   (
   source_pagename varchar(100),
   destination_pagename varchar(100),
   primary key (source_pagename, destination_pagename)
   );""")

 if config.db_type == 'mysql':
   cursor.execute("""create table events
   (
   uid mediumint primary key,
   event_time double,
   posted_by varchar(100),
   text mediumtext,
   location mediumtext,
   event_name mediumtext,
   posted_by_ip char(16),
   posted_time double 
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table events
   (
   uid int primary key,
   event_time double precision,
   posted_by varchar(100),
   text text,
   location text,
   event_name text,
   posted_by_ip char(16),
   posted_time double precision
   );""")

 cursor.execute("CREATE INDEX events_event_time on events (event_time);")
 cursor.execute("CREATE INDEX events_posted_by on events (posted_by);")
 cursor.execute("CREATE INDEX events_posted_by_ip on events (posted_by_ip);")
 cursor.execute("CREATE INDEX events_posted_time on events (posted_time);")
 
 if config.db_type == 'mysql':
   cursor.execute("""create table images
   (
   name varchar(100) not null,
   image mediumblob not null,
   uploaded_time double not null,
   uploaded_by char(20),
   attached_to_pagename varchar(255) not null,
   uploaded_by_ip char(16),
   xsize smallint,
   ysize smallint,
   primary key (name, attached_to_pagename)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table images
   (
   name varchar(100) not null,
   image bytea not null,
   uploaded_time double precision not null,
   uploaded_by char(20),
   attached_to_pagename varchar(255) not null,
   uploaded_by_ip char(16),
   xsize smallint,
   ysize smallint,
   primary key (name, attached_to_pagename)
   );""")

 cursor.execute("CREATE INDEX images_uploaded_by on images (uploaded_by);")
 cursor.execute("CREATE INDEX images_uploaded_time on images (uploaded_time);")
 
 if config.db_type == 'mysql':
   cursor.execute("""create table oldImages
   (
   name varchar(100) not null,
   image mediumblob not null,
   uploaded_time double not null,
   uploaded_by char(20),
   attached_to_pagename varchar(255) not null,
   deleted_time double,
   deleted_by char(20),
   uploaded_by_ip char(16),
   deleted_by_ip char(16),
   xsize smallint,
   ysize smallint,
   primary key (name, attached_to_pagename, uploaded_time)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table oldImages
   (
   name varchar(100) not null,
   image bytea not null,
   uploaded_time double precision not null,
   uploaded_by char(20),
   attached_to_pagename varchar(255) not null,
   deleted_time double precision,
   deleted_by char(20),
   uploaded_by_ip char(16),
   deleted_by_ip char(16),
   xsize smallint,
   ysize smallint,
   primary key (name, attached_to_pagename, uploaded_time)
   );""")
 
 
 cursor.execute("CREATE INDEX oldImages_deleted_time on oldImages (deleted_time);")
 
 if config.db_type == 'mysql':
   #throw-away and easily regenerated data
   cursor.execute("""create table thumbnails
   (              
   xsize smallint,
   ysize smallint,
   name varchar(100),
   attached_to_pagename varchar(100),
   image mediumblob,
   last_modified double,
   primary key (name, attached_to_pagename)
   ) type=MyISAM;""")
 elif config.db_type == 'postgres':
   #throw-away and easily regenerated data
   cursor.execute("""create table thumbnails
   (              
   xsize smallint,
   ysize smallint,
   name varchar(100),
   attached_to_pagename varchar(100),
   image bytea,
   last_modified double precision,
   primary key (name, attached_to_pagename)
   );""")

 if config.db_type == 'mysql':
   cursor.execute("""create table imageCaptions
   (
    image_name varchar(100),
    attached_to_pagename varchar(100),
    linked_from_pagename varchar(100),
    caption text,
    primary key (image_name, attached_to_pagename, linked_from_pagename)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table imageCaptions
   (
    image_name varchar(100),
    attached_to_pagename varchar(100),
    linked_from_pagename varchar(100),
    caption text,
    primary key (image_name, attached_to_pagename, linked_from_pagename)
   );""")

 if config.db_type == 'mysql':
   cursor.execute("""create table mapCategoryDefinitions
   (
   id int,
   img varchar(100),
   name varchar(100),
   primary key (id)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table mapCategoryDefinitions
   (
   id int,
   img varchar(100),
   name varchar(100),
   primary key (id)
   );""")

 if config.db_type == 'mysql':
   cursor.execute("""create table mapPoints
   (
     pagename varchar(100),
     x varchar(100),
     y varchar(100),
     created_time double,
     created_by char(20),
     created_by_ip char(16),
     id int,
     primary key (pagename, x, y)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table mapPoints
   (
     pagename varchar(100),
     x varchar(100),
     y varchar(100),
     created_time double precision,
     created_by char(20),
     created_by_ip char(16),
     id int,
     primary key (pagename, x, y)
   );""")
 
 cursor.execute("""CREATE INDEX mapPoints_created_time on mapPoints (created_time);""")
 cursor.execute("""CREATE INDEX mapPoints_id on mapPoints (id);""")
 
 if config.db_type == 'mysql':
   cursor.execute("""create table oldMapPoints
   (
     pagename varchar(100),
     x varchar(100),
     y varchar(100),
     created_time double,
     created_by char(20),
     created_by_ip char(16),
     deleted_time double,
     deleted_by char(20),
     deleted_by_ip char(16),
     primary key (pagename, x, y, deleted_time)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table oldMapPoints
   (
     pagename varchar(100),
     x varchar(100),
     y varchar(100),
     created_time double precision,
     created_by char(20),
     created_by_ip char(16),
     deleted_time double precision,
     deleted_by char(20),
     deleted_by_ip char(16),
     primary key (pagename, x, y, deleted_time)
   );""")

 cursor.execute("CREATE INDEX oldMapPoints_deleted_time on oldMapPoints (deleted_time);")
 
 if config.db_type == 'mysql':
   cursor.execute("""create table mapPointCategories
   (
     pagename varchar(100),
     x varchar(100),
     y varchar(100),
     id int,
     primary key (pagename, x, y, id)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table mapPointCategories
     (
       pagename varchar(100),
       x varchar(100),
       y varchar(100),
       id int,
       primary key (pagename, x, y, id)
     );""")
 
 if config.db_type == 'mysql':
   cursor.execute("""create table oldMapPointCategories
   (
     pagename varchar(100),
     x varchar(100),
     y varchar(100),
     id int,
     deleted_time double,
     primary key (pagename, x, y, id, deleted_time)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table oldMapPointCategories
   (
     pagename varchar(100),
     x varchar(100),
     y varchar(100),
     id int,
     deleted_time double precision,
     primary key (pagename, x, y, id, deleted_time)
   );""")

 if config.db_type == 'mysql':
   cursor.execute("""create table pageDependencies
   (
     page_that_depends varchar(100),
     source_page varchar(100),
     primary key (page_that_depends, source_page)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table pageDependencies
   (
     page_that_depends varchar(100),
     source_page varchar(100),
     primary key (page_that_depends, source_page)
   );""")

 if config.db_type == 'mysql':
   cursor.execute("""create table metadata
   (
     pagename varchar(100),
     type varchar(100),
     name varchar(100),
     value varchar(100),
     primary key (pagename, type, name)
   ) type=InnoDB;""")
 elif config.db_type == 'postgres':
   cursor.execute("""create table metadata
   (
     pagename varchar(100),
     type varchar(100),
     name varchar(100),
     value varchar(100),
     primary key (pagename, type, name)
   );""")

 print "tables created"


def create_views(cursor):
 print "creating views..."
 cursor.execute("CREATE VIEW eventChanges as SELECT 'Events Board' as name, events.posted_time as changeTime, users.id as id, 'NEWEVENT' as editType, events.event_name as comment, events.posted_by_IP as userIP from events, users where users.name=events.posted_by;")
 cursor.execute("CREATE VIEW deletedImageChanges as SELECT oldImages.attached_to_pagename as name, oldImages.deleted_time as changeTime, oldImages.deleted_by as id, 'ATTDEL' as editType, name as comment, oldImages.deleted_by_ip as userIP from oldImages;")
 cursor.execute("CREATE VIEW oldImageChanges as SELECT oldImages.attached_to_pagename as name, oldImages.uploaded_time as changeTime, oldImages.uploaded_by as id, 'ATTNEW' as editType, name as comment, oldImages.uploaded_by_ip as userIP from oldImages;")
 cursor.execute("CREATE VIEW currentImageChanges as SELECT images.attached_to_pagename as name, images.uploaded_time as changeTime, images.uploaded_by as id, 'ATTNEW' as editType, name as comment, images.uploaded_by_ip as userIP from images;")
 cursor.execute("CREATE VIEW pageChanges as SELECT name, editTime as changeTime, userEdited as id, editType, comment, userIP from allPages;")
 cursor.execute("CREATE VIEW currentMapChanges as SELECT mapPoints.pagename as name, mapPoints.created_time as changeTime, mapPoints.created_by as id, 'SAVEMAP' as editType, NULL as comment, mapPoints.created_by_ip as userIP from mapPoints;")
 cursor.execute("CREATE VIEW oldMapChanges as SELECT oldMapPoints.pagename as name, oldMapPoints.created_time as changeTime, oldMapPoints.created_by as id, 'SAVEMAP' as editType, NULL as comment, oldMapPoints.created_by_ip as userIP from oldMapPoints;")
 cursor.execute("CREATE VIEW deletedMapChanges as SELECT oldMapPoints.pagename as name, oldMapPoints.deleted_time as changeTime, oldMapPoints.deleted_by as id, 'SAVEMAP' as editType, NULL as comment, oldMapPoints.deleted_by_ip as userIP from oldMapPoints;")
 print "views created"

def create_other_stuff(cursor):
 print "creating other stuff..."
 cursor.execute("INSERT into mapCategoryDefinitions values (1, 'food.png', 'Restaurants');")
 cursor.execute("INSERT into mapCategoryDefinitions values (2, 'dollar.png', 'Shopping');")
 cursor.execute("INSERT into mapCategoryDefinitions values (3, 'hand.png', 'Services');")
 cursor.execute("INSERT into mapCategoryDefinitions values (4, 'run.png', 'Parks & Recreation');")
 cursor.execute("INSERT into mapCategoryDefinitions values (5, 'people.png', 'Community');")
 cursor.execute("INSERT into mapCategoryDefinitions values (6, 'arts.png', 'Arts & Entertainment');")
 cursor.execute("INSERT into mapCategoryDefinitions values (7, 'edu.png', 'Education');")
 cursor.execute("INSERT into mapCategoryDefinitions values (9, 'head.png', 'People');")
 cursor.execute("INSERT into mapCategoryDefinitions values (10, 'gov.png', 'Government');")
 cursor.execute("INSERT into mapCategoryDefinitions values (11, 'bike.png', 'Bars & Night Life');")

 cursor.execute("INSERT into mapCategoryDefinitions values (12, 'coffee.png', 'Cafes');")
 cursor.execute("INSERT into mapCategoryDefinitions values (13, 'house.png', 'Housing');")
 cursor.execute("INSERT into mapCategoryDefinitions values (14, 'wifi.png', 'WiFi Hot Spots');")
 cursor.execute("INSERT into mapCategoryDefinitions values (99, NULL, 'Other');")
 print "other stuff created"

def insert_basic_pages(cursor):
 print "inserting basic pages..."
 for pagename, pagetext in basic_pages.iteritems():
   cursor.execute("insert into curPages values (%(pagename)s, %(pagetext)s, NULL, UNIX_TIMESTAMP('2005-11-09 14:44:00'), NULL, NULL);", {'pagename':pagename, 'pagetext':pagetext})
   cursor.execute("insert into allPages values (%(pagename)s, %(pagetext)s, UNIX_TIMESTAMP('2005-11-09 14:44:00'), NULL, 'SAVENEW', 'System page', NULL);", {'pagename':pagename, 'pagetext':pagetext})
 print "basic pages inserted"

def build_search_index():
  # builds the title and full text search indexes.
  if not config.has_xapian:
    print "You don't have Xapian installed...skipping configuration of search index."
    return

  if not os.path.exists(config.search_db_location):
    # create it if it doesn't exist, we don't want to create
    # intermediates though
    os.mkdir(config.search_db_location)

  # prune existing db directories, do this explicitly in case third party
  # extensions use this directory (they really shouldn't)
  for db in ('title', 'text'):
    dbpath = os.path.join(config.search_db_location, db)
    if os.path.exists(dbpath):
      shutil.rmtree(dbpath)

  print "Building search index..."
  from Sycamore import request, wikiutil, search
  req = request.RequestDummy()
  pages = wikiutil.getPageList(req, objects=True)
  for page in pages:
    print "  %s added to search index." % page.page_name
    search.index(page)

db = wikidb.connect()
cursor = db.cursor()
init_db(cursor)
create_tables(cursor)
create_views(cursor)
create_other_stuff(cursor)
insert_basic_pages(cursor)
build_search_index()
db.commit()
db.close()
