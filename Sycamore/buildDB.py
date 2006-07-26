# Build a wiki database from scratch.  You should run this the FIRST TIME you install your wiki.
import sys, os, shutil
import __init__ # woo hackmagic
__directory__ = os.path.dirname(__file__)
share_directory = os.path.abspath(os.path.join(__directory__, '..', 'share'))
sys.path.extend([share_directory]),
from Sycamore import wikidb, config, wikiutil, maintenance
from Sycamore.wikiutil import quoteFilename, unquoteFilename
from Sycamore.action import Files

class FlatPage(object):
    """
    A basic flat page object containing text and possibly files to be imported.
    """
    def __init__(self, text=""):
        self.text = text
        self.files = []
    def add_file(self, filename, filecontent):
        self.files.append((filename, filecontent))
  
def init_basic_pages():
    """
    Initializes basic pages from share/initial_pages directory.
    """
    basic_pages = {}
    # We do the basic database population here
    page_list = map(unquoteFilename, filter(lambda x: not x.startswith('.'), os.listdir(os.path.join(share_directory, 'initial_pages'))))
    for pagename in page_list:
       page_loc = os.path.join(share_directory, 'initial_pages', quoteFilename(pagename))
       page_text_file = open(os.path.join(page_loc, "text"))
       page_text = ''.join(page_text_file.readlines())
       page_text_file.close()

       basic_pages[pagename] = FlatPage(text=page_text)

       if os.path.exists(os.path.join(page_loc, "files")):
         file_list = map(unquoteFilename, filter(lambda x: not x.startswith('.'), os.listdir(os.path.join(page_loc, "files"))))
         for filename in file_list:
           file = open(os.path.join(page_loc, "files", quoteFilename(filename)))
           file_content = ''.join(file.readlines())
           file.close()
           basic_pages[pagename].files.append((filename, file_content))

    return basic_pages
    
    
def init_db(cursor):
  if config.db_type == 'postgres':
    cursor.execute("CREATE FUNCTION UNIX_TIMESTAMP(timestamp) RETURNS integer AS 'SELECT date_part(''epoch'', $1)::int4 AS result' language 'sql';", isWrite=True)

def create_tables(cursor):
  print "creating tables.."
  if config.db_type == 'mysql':
    cursor.execute("""create table curPages
      (
      name varchar(100) primary key not null,
      text mediumtext,
      cachedText mediumblob,
      editTime double,
      cachedTime double,
      userEdited char(20),
      propercased_name varchar(100) not null 
      ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table curPages
      (
      name varchar(100) primary key not null,
      text text,
      cachedText bytea,
      editTime double precision,
      cachedTime double precision,
      userEdited char(20),
      propercased_name varchar(100) not null
      );""", isWrite=True)
 
  cursor.execute("CREATE INDEX curPages_userEdited on curPages (userEdited);")
  if config.db_type == 'mysql':
    cursor.execute("""create table allPages
      (
      name varchar(100) not null,
      text mediumtext,
      editTime double,
      userEdited char(20),
      editType CHAR(30) CHECK (editType in ('SAVE','SAVENEW','ATTNEW','ATTDEL','RENAME','NEWEVENT','COMMENT_MACRO','SAVE/REVERT','DELETE', 'SAVEMAP')),
      comment varchar(194),
      userIP char(16),
      propercased_name varchar(100) not null,
      primary key(name, editTime)
      ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table allPages
      (
      name varchar(100) not null,
      text text,
      editTime double precision,
      userEdited char(20),
      editType CHAR(30) CHECK (editType in ('SAVE','SAVENEW','ATTNEW','ATTDEL','RENAME','NEWEVENT','COMMENT_MACRO','SAVE/REVERT','DELETE', 'SAVEMAP')),
      comment varchar(194),
      userIP inet,
      propercased_name varchar(100) not null,
      primary key (name, editTime)
      );""", isWrite=True)
 
  cursor.execute("CREATE INDEX allPages_userEdited on allPages (userEdited);", isWrite=True)
  cursor.execute("CREATE INDEX allPages_userIP on allPages (userIP);", isWrite=True)
  cursor.execute("CREATE INDEX editTime on allPages (editTime);", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table users
     (
     id char(20) primary key not null,
     name varchar(100) unique not null,
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
     tz_offset int,
     propercased_name varchar(100) not null
     ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
   cursor.execute("""create table users
     (
     id char(20) primary key not null,
     name varchar(100) unique not null,
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
     tz_offset int,
     propercased_name varchar(100) not null
     );""", isWrite=True)
 
  cursor.execute("CREATE INDEX users_name on users (name);", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table userFavorites
    (
    username varchar(100) not null,
    page varchar(100) not null,
    viewTime double,
    primary key (username, page)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table userFavorites
    (
    username varchar(100) not null,
    page varchar(100) not null,
    viewTime double precision,
    primary key (username, page)
    );""", isWrite=True)
 
  if config.db_type == 'mysql':
    #This is throw-away data. User sessions aren't that important so we'll use a MyISAM table for speed
    cursor.execute("""create table userSessions
    (
    user_id char(20) not null,
    session_id char(28) not null,
    secret char(28) not null,
    expire_time double,
    primary key (user_id, session_id)
    ) ENGINE=MyISAM CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    #This is throw-away data. User sessions aren't that important so we'll use a MyISAM table for speed
    cursor.execute("""create table userSessions
    (
    user_id char(20) not null,
    session_id char(28) not null,
    secret char(28) not null,
    expire_time double precision,
    primary key (user_id, session_id)
    );""", isWrite=True)
 
  cursor.execute("CREATE INDEX userSessions_expire_time on userSessions (expire_time);", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table links
    (
    source_pagename varchar(100) not null,
    destination_pagename varchar(100) not null,
    destination_pagename_propercased varchar(100) not null,
    primary key (source_pagename, destination_pagename)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table links
    (
    source_pagename varchar(100) not null,
    destination_pagename varchar(100) not null,
    destination_pagename_propercased varchar(100) not null,
    primary key (source_pagename, destination_pagename)
    );""", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table events
    (
    uid mediumint primary key not null,
    event_time double not null,
    posted_by varchar(100),
    text mediumtext not null,
    location mediumtext not null,
    event_name mediumtext not null,
    posted_by_ip char(16),
    posted_time double 
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table events
    (
    uid int primary key not null,
    event_time double precision not null,
    posted_by varchar(100),
    text text not null,
    location text not null,
    event_name text not null,
    posted_by_ip inet,
    posted_time double precision
    );""", isWrite=True)
 
  cursor.execute("CREATE INDEX events_event_time on events (event_time);", isWrite=True)
  cursor.execute("CREATE INDEX events_posted_by on events (posted_by);", isWrite=True)
  cursor.execute("CREATE INDEX events_posted_by_ip on events (posted_by_ip);", isWrite=True)
  cursor.execute("CREATE INDEX events_posted_time on events (posted_time);", isWrite=True)
  
  if config.db_type == 'mysql':
    cursor.execute("""create table files
    (
    name varchar(100) not null,
    file mediumblob not null,
    uploaded_time double not null,
    uploaded_by char(20),
    attached_to_pagename varchar(255) not null,
    uploaded_by_ip char(16),
    attached_to_pagename_propercased varchar(255) not null,
    primary key (name, attached_to_pagename)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table files
    (
    name varchar(100) not null,
    file bytea not null,
    uploaded_time double precision not null,
    uploaded_by char(20),
    attached_to_pagename varchar(255) not null,
    uploaded_by_ip inet,
    attached_to_pagename_propercased varchar(255) not null,
    primary key (name, attached_to_pagename)
    );""", isWrite=True)
 
  cursor.execute("CREATE INDEX filess_uploaded_by on files (uploaded_by);", isWrite=True)
  cursor.execute("CREATE INDEX files_uploaded_time on files (uploaded_time);", isWrite=True)
  
  if config.db_type == 'mysql':
    cursor.execute("""create table oldFiles
    (
    name varchar(100) not null,
    file mediumblob not null,
    uploaded_time double not null,
    uploaded_by char(20),
    attached_to_pagename varchar(255) not null,
    deleted_time double,
    deleted_by char(20),
    uploaded_by_ip char(16),
    deleted_by_ip char(16),
    attached_to_pagename_propercased varchar(255) not null,
    primary key (name, attached_to_pagename, uploaded_time)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table oldFiles
    (
    name varchar(100) not null,
    file bytea not null,
    uploaded_time double precision not null,
    uploaded_by char(20),
    attached_to_pagename varchar(255) not null,
    deleted_time double precision,
    deleted_by char(20),
    uploaded_by_ip inet,
    deleted_by_ip inet,
    attached_to_pagename_propercased varchar(255) not null,
    primary key (name, attached_to_pagename, uploaded_time)
    );""", isWrite=True)
  
  
  cursor.execute("CREATE INDEX oldFiles_deleted_time on oldFiles (deleted_time);", isWrite=True)
  
  if config.db_type == 'mysql':
    #throw-away and easily regenerated data
    cursor.execute("""create table thumbnails
    (              
    xsize smallint,
    ysize smallint,
    name varchar(100) not null,
    attached_to_pagename varchar(100) not null,
    image mediumblob not null,
    last_modified double,
    primary key (name, attached_to_pagename)
    ) ENGINE=MyISAM CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    #throw-away and easily regenerated data
    cursor.execute("""create table thumbnails
    (              
    xsize smallint,
    ysize smallint,
    name varchar(100) not null,
    attached_to_pagename varchar(100) not null,
    image bytea not null,
    last_modified double precision,
    primary key (name, attached_to_pagename)
    );""", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table imageInfo
    (
    name varchar(100) not null,
    attached_to_pagename varchar(255) not null,
    xsize smallint,
    ysize smallint,
    primary key (name, attached_to_pagename)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table imageInfo
    (
    name varchar(100) not null,
    attached_to_pagename varchar(255) not null,
    xsize smallint,
    ysize smallint,
    primary key (name, attached_to_pagename)
    );""", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table oldImageInfo
    (
    name varchar(100) not null,
    attached_to_pagename varchar(255) not null,
    xsize smallint,
    ysize smallint,
    uploaded_time double not null,
    primary key (name, attached_to_pagename, uploaded_time)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table oldImageInfo
    (
    name varchar(100) not null,
    attached_to_pagename varchar(255) not null,
    xsize smallint,
    ysize smallint,
    uploaded_time double precision not null,
    primary key (name, attached_to_pagename, uploaded_time)
    );""", isWrite=True)
 
 
  if config.db_type == 'mysql':
    cursor.execute("""create table imageCaptions
    (
     image_name varchar(100) not null,
     attached_to_pagename varchar(100) not null,
     linked_from_pagename varchar(100),
     caption text not null,
     primary key (image_name, attached_to_pagename, linked_from_pagename)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table imageCaptions
    (
     image_name varchar(100) not null,
     attached_to_pagename varchar(100) not null,
     linked_from_pagename varchar(100),
     caption text not null,
     primary key (image_name, attached_to_pagename, linked_from_pagename)
    );""", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table mapCategoryDefinitions
    (
    id int not null,
    img varchar(100),
    name varchar(100) not null,
    primary key (id)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table mapCategoryDefinitions
    (
    id int not null,
    img varchar(100),
    name varchar(100) not null,
    primary key (id)
    );""", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table mapPoints
    (
      pagename varchar(100) not null,
      x varchar(100) not null,
      y varchar(100) not null,
      created_time double,
      created_by char(20),
      created_by_ip char(16),
      id int,
      pagename_propercased varchar(100) not null,
      primary key (pagename, x, y)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table mapPoints
    (
      pagename varchar(100) not null,
      x varchar(100) not null,
      y varchar(100) not null,
      created_time double precision,
      created_by char(20),
      created_by_ip inet,
      id int,
      pagename_propercased varchar(100) not null,
      primary key (pagename, x, y)
    );""", isWrite=True)
  
  cursor.execute("""CREATE INDEX mapPoints_created_time on mapPoints (created_time);""", isWrite=True)
  cursor.execute("""CREATE INDEX mapPoints_id on mapPoints (id);""", isWrite=True)
  
  if config.db_type == 'mysql':
    cursor.execute("""create table oldMapPoints
    (
      pagename varchar(100) not null,
      x varchar(100) not null,
      y varchar(100) not null,
      created_time double,
      created_by char(20),
      created_by_ip char(16),
      deleted_time double,
      deleted_by char(20),
      deleted_by_ip char(16),
      pagename_propercased varchar(100) not null,
      primary key (pagename, x, y, deleted_time)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table oldMapPoints
    (
      pagename varchar(100) not null,
      x varchar(100) not null,
      y varchar(100) not null,
      created_time double precision,
      created_by char(20),
      created_by_ip inet,
      deleted_time double precision,
      deleted_by char(20),
      deleted_by_ip inet,
      pagename_propercased varchar(100) not null,
      primary key (pagename, x, y, deleted_time)
    );""", isWrite=True)
 
  cursor.execute("CREATE INDEX oldMapPoints_deleted_time on oldMapPoints (deleted_time);", isWrite=True)
  cursor.execute("CREATE INDEX oldMapPoints_created_time on oldMapPoints (created_time);", isWrite=True)
  
  if config.db_type == 'mysql':
    cursor.execute("""create table mapPointCategories
    (
      pagename varchar(100) not null,
      x varchar(100) not null,
      y varchar(100) not null,
      id int not null,
      primary key (pagename, x, y, id)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table mapPointCategories
      (
        pagename varchar(100) not null,
        x varchar(100) not null,
        y varchar(100) not null,
        id int not null,
        primary key (pagename, x, y, id)
      );""", isWrite=True)
  
  if config.db_type == 'mysql':
    cursor.execute("""create table oldMapPointCategories
    (
      pagename varchar(100) not null,
      x varchar(100) not null,
      y varchar(100) not null,
      id int not null,
      deleted_time double,
      primary key (pagename, x, y, id, deleted_time)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table oldMapPointCategories
    (
      pagename varchar(100) not null,
      x varchar(100) not null,
      y varchar(100) not null,
      id int not null,
      deleted_time double precision,
      primary key (pagename, x, y, id, deleted_time)
    );""", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table pageDependencies
    (
      page_that_depends varchar(100) not null,
      source_page varchar(100) not null,
      primary key (page_that_depends, source_page)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table pageDependencies
    (
      page_that_depends varchar(100) not null,
      source_page varchar(100) not null,
      primary key (page_that_depends, source_page)
    );""", isWrite=True)
 
  if config.db_type == 'mysql':
    cursor.execute("""create table metadata
    (
      pagename varchar(100),
      type varchar(100),
      name varchar(100),
      value varchar(100),
      primary key (pagename, type, name)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
  elif config.db_type == 'postgres':
    cursor.execute("""create table metadata
    (
      pagename varchar(100),
      type varchar(100),
      name varchar(100),
      value varchar(100),
      primary key (pagename, type, name)
    );""", isWrite=True)
 
  print "tables created"


def create_views(cursor):
 print "creating views..."
 if config.db_type == 'mysql':
   cursor.execute("CREATE VIEW eventChanges as SELECT 'Events Board' as name, events.posted_time as changeTime, users.id as id, 'NEWEVENT' as editType, events.event_name as comment, events.posted_by_IP as userIP, 'Events Board' as propercased_name from events, users where users.propercased_name=events.posted_by;", isWrite=True)
   cursor.execute("CREATE VIEW deletedFileChanges as SELECT oldFiles.attached_to_pagename as name, oldFiles.deleted_time as changeTime, oldFiles.deleted_by as id, 'ATTDEL' as editType, name as comment, oldFiles.deleted_by_ip as userIP, oldFiles.attached_to_pagename_propercased as propercased_name from oldFiles;", isWrite=True)
   cursor.execute("CREATE VIEW oldFileChanges as SELECT oldFiles.attached_to_pagename as name, oldFiles.uploaded_time as changeTime, oldFiles.uploaded_by as id, 'ATTNEW' as editType, name as comment, oldFiles.uploaded_by_ip as userIP, oldFiles.attached_to_pagename_propercased as propercased_name from oldFiles;", isWrite=True)
   cursor.execute("CREATE VIEW currentFileChanges as SELECT files.attached_to_pagename as name, files.uploaded_time as changeTime, files.uploaded_by as id, 'ATTNEW' as editType, name as comment, files.uploaded_by_ip as userIP, files.attached_to_pagename_propercased as propercased_name from files;", isWrite=True)
   cursor.execute("CREATE VIEW pageChanges as SELECT name, editTime as changeTime, userEdited as id, editType, comment, userIP, propercased_name from allPages;", isWrite=True)
   cursor.execute("CREATE VIEW currentMapChanges as SELECT mapPoints.pagename as name, mapPoints.created_time as changeTime, mapPoints.created_by as id, 'SAVEMAP' as editType, NULL as comment, mapPoints.created_by_ip as userIP, mapPoints.pagename_propercased as propercased_name from mapPoints;", isWrite=True)
   cursor.execute("CREATE VIEW oldMapChanges as SELECT oldMapPoints.pagename as name, oldMapPoints.created_time as changeTime, oldMapPoints.created_by as id, 'SAVEMAP' as editType, NULL as comment, oldMapPoints.created_by_ip as userIP, oldMapPoints.pagename_propercased as propercased_name from oldMapPoints;", isWrite=True)
   cursor.execute("CREATE VIEW deletedMapChanges as SELECT oldMapPoints.pagename as name, oldMapPoints.deleted_time as changeTime, oldMapPoints.deleted_by as id, 'SAVEMAP' as editType, NULL as comment, oldMapPoints.deleted_by_ip as userIP, oldMapPoints.pagename_propercased as propercased_name from oldMapPoints;", isWrite=True)
 elif config.db_type == 'postgres':
   cursor.execute("CREATE VIEW eventChanges as SELECT char 'Events Board' as name, events.posted_time as changeTime, users.id as id, char 'NEWEVENT' as editType, events.event_name as comment, events.posted_by_IP as userIP from events, users where users.propercased_name=events.posted_by;", isWrite=True)
   cursor.execute("CREATE VIEW deletedFileChanges as SELECT oldFiles.attached_to_pagename as name, oldFiles.deleted_time as changeTime, oldFiles.deleted_by as id, char 'ATTDEL' as editType, name as comment, oldFiles.deleted_by_ip as userIP, oldFiles.attached_to_pagename_propercased as propercased_name from oldFiles;", isWrite=True)
   cursor.execute("CREATE VIEW oldFileChanges as SELECT oldFiles.attached_to_pagename as name, oldFiles.uploaded_time as changeTime, oldFiles.uploaded_by as id, char 'ATTNEW' as editType, name as comment, oldFiles.uploaded_by_ip as userIP, oldFiles.attached_to_pagename_propercased as propercased_name from oldFiles;", isWrite=True)
   cursor.execute("CREATE VIEW currentFileChanges as SELECT files.attached_to_pagename as name, files.uploaded_time as changeTime, files.uploaded_by as id, char 'ATTNEW' as editType, name as comment, files.uploaded_by_ip as userIP, files.attached_to_pagename_propercased as propercased_name from files;", isWrite=True)
   cursor.execute("CREATE VIEW pageChanges as SELECT name, editTime as changeTime, userEdited as id, editType, comment, userIP, propercased_name from allPages;", isWrite=True)
   cursor.execute("CREATE VIEW currentMapChanges as SELECT mapPoints.pagename as name, mapPoints.created_time as changeTime, mapPoints.created_by as id, char 'SAVEMAP' as editType, char ''as comment, mapPoints.created_by_ip as userIP, mapPoints.pagename_propercased as propercased_name from mapPoints;", isWrite=True)
   cursor.execute("CREATE VIEW oldMapChanges as SELECT oldMapPoints.pagename as name, oldMapPoints.created_time as changeTime, oldMapPoints.created_by as id, char 'SAVEMAP' as editType, char '' as comment, oldMapPoints.created_by_ip as userIP, oldMapPoints.pagename_propercased as propercased_name from oldMapPoints;", isWrite=True)
   cursor.execute("CREATE VIEW deletedMapChanges as SELECT oldMapPoints.pagename as name, oldMapPoints.deleted_time as changeTime, oldMapPoints.deleted_by as id, char 'SAVEMAP' as editType, char '' as comment, oldMapPoints.deleted_by_ip as userIP, oldMapPoints.pagename_propercased as propercased_name from oldMapPoints;", isWrite=True)

 print "views created"

def create_other_stuff(cursor):
 print "creating other stuff..."
 cursor.execute("INSERT into mapCategoryDefinitions values (1, 'food.png', 'Restaurants');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (2, 'dollar.png', 'Shopping');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (3, 'hand.png', 'Services');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (4, 'run.png', 'Parks & Recreation');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (5, 'people.png', 'Community');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (6, 'arts.png', 'Arts & Entertainment');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (7, 'edu.png', 'Education');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (9, 'head.png', 'People');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (10, 'gov.png', 'Government');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (11, 'bike.png', 'Bars & Night Life');", isWrite=True)

 cursor.execute("INSERT into mapCategoryDefinitions values (12, 'coffee.png', 'Cafes');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (13, 'house.png', 'Housing');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (14, 'wifi.png', 'WiFi Hot Spots');", isWrite=True)
 cursor.execute("INSERT into mapCategoryDefinitions values (99, NULL, 'Other');", isWrite=True)
 print "other stuff created"

def insert_pages(cursor, flat_page_dict=None, plist=None, without_files=False):
 print "inserting basic pages..."
 if not flat_page_dict: flat_page_dict = basic_pages
 if not plist: plist = flat_page_dict.keys()
 file_dict = { 'uploaded_time': 0, 'uploaded_by': None, 'uploaded_by_ip': None }
 for pagename in plist:
   flatpage = flat_page_dict[pagename]
   cursor.execute("INSERT into curPages (name, text, cachedText, editTime, cachedTime, userEdited, propercased_name) values (%(pagename)s, %(pagetext)s, NULL, UNIX_TIMESTAMP('2005-11-09 14:44:00'), NULL, NULL, %(propercased_name)s);", {'pagename':pagename.lower(), 'pagetext':flatpage.text, 'propercased_name':pagename}, isWrite=True)
   cursor.execute("INSERT into allPages (name, text, editTime, userEdited, editType, comment, userIP, propercased_name) values (%(pagename)s, %(pagetext)s, UNIX_TIMESTAMP('2005-11-09 14:44:00'), NULL, 'SAVENEW', 'System page', NULL, %(propercased_name)s);", {'pagename':pagename.lower(), 'pagetext':flatpage.text, 'propercased_name':pagename}, isWrite=True)
   file_dict['pagename'] = pagename
   for filename, content in flatpage.files:
      file_dict['filename'] = filename
      file_dict['filecontent'] = content
      if wikiutil.isImage(filename):
          xsize, ysize = Files.openImage(content).size
          file_dict['xsize'] = xsize
          file_dict['ysize'] = ysize
      wikidb.putFile(req, file_dict)


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
  from Sycamore import wikiutil, search
  pages = wikiutil.getPageList(req, objects=True)
  for page in pages:
    print "  %s added to search index." % page.page_name
    search.add_to_index(page)


basic_pages = init_basic_pages()

if __name__ == '__main__':
  from Sycamore import request
  req = request.RequestDummy()
  cursor = req.cursor
  init_db(cursor)
  create_tables(cursor)
  create_views(cursor)
  create_other_stuff(cursor)
  insert_pages(cursor)
  build_search_index()

  plist = wikiutil.getPageList(req)
  req.db_disconnect()

  maintenance.buildCaches(plist) 
