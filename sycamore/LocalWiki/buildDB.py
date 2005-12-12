import sys
sys.path.extend(['/usr/local/lib/python2.3/site-packages','/var/www/installhtml/dwiki'])
from LocalWiki import wikidb

# We do the basic database population here
userpref_text = """#acl AdminGroup:admin,read,write,delete,revert All:read
##language:en
[[UserPreferences]]

= First time =
Please fill out '''[[GetText(Name)]]''', '''[[GetText(Password)]]''', '''[[GetText(Password repeat)]]''' and '''[[GetText(Email)]]'''.

(!) Your email is needed for you to be able to get notifications on page changes and to recover lost login data.

If you click on '''[[GetText(Create Profile)]]''', a user profile will be created for you and you will be logged in immediately.

= Logging in =
If want to re-login, just use '''[[GetText(Name)]]''' and '''[[GetText(Password)]]''' and click on '''[[GetText(Login)]]'''.

If you '''forgot your password''', attempt to log in via the login box in the upper right hand corner of the screen and you will be given further instruction.

= Changing settings =
'''[[GetText(Save)]]''' updates your profile (stored on the wiki server).

= Logging out =
'''[[GetText(Logout)]]''' clears the cookie created at login.

= The Cookie =
/!\ The "ID", shown in the response page, gets saved as a cookie in your browser for the system to temporarily recognize you. It will expire next midnight - except if you choose '''[[GetText(Remember login information forever)]]''' (after being logged in), then the cookie won't expire."""

rc_text = """#acl AdminGroup:admin,read,write,delete,revert All:read
||<bgcolor='#ffffaa'>'''TIP''':  [[RandomQuote(Quick Wiki Tips)]]||
[[BR]]
[[RecentChanges]]
[[BR]]

||<:> [[Icon(diffrc)]] || marks older pages that have at least one backup version stored (click for an author ''diff''erence)||
||<:> [[Icon(updated)]] || marks pages edited since you last pressed 'clear observed changes' (click to see differences since you cleared)||
||<:> [[Icon(new)]] || marks new pages||
----
This page contains a list of recent changes in this wiki of '''[[PageCount]] pages''' (more system information on ["System Info"] -- there are also ["User Statistics"])."""

def create_tables(cursor):
 cursor.execute("""create table curPages
   (
   name varchar(255) primary key,
   text mediumtext,
   cachedText mediumblob,
   editTime double,
   cachedTime double,
   userEdited char(19)
   ) type=InnoDB;""")
 cursor.execute("alter table curPages add index userEdited(userEdited);")
 cursor.execute("""create table allPages
   (
   name varchar(255),
   text mediumtext,
   editTime double,
   userEdited char(19),
   editType enum('SAVE','SAVENEW','ATTNEW','ATTDEL','RENAME','NEWEVENT','COMMENT_MACRO','SAVE/REVERT','DELETE'),
   comment varchar(81),
   userIP char(16),
   primary key(name, editTime)
   ) type=InnoDB;""")

 cursor.execute("alter table allPages add index userEdited(userEdited);")
 cursor.execute("alter table allPages add index userIP(userIP);")

 cursor.execute("""create table users
  (
  id char(19) primary key,
  name varchar(255),
  email varchar(255),
  enc_password varchar(255),
  language varchar(80),
  remember_me tinyint,
  css_url varchar(255),
  disabled tinyint,
  edit_cols smallint,
  edit_rows smallint,
  edit_on_doubleclick tinyint,
  theme_name char(40),
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

 cursor.execute("alter table users add index name(name);")

 cursor.execute("""create table userFavorites
  (
  username varchar(255),
  page varchar(255),
  viewTime double,
  primary key (username, page)
  ) type=InnoDB;""")

 #This is throw-away data. User sessions aren't that important so we'll use a MyISAM table for speed
 cursor.execute("""create table userSessions
 (
 user_id char(19),
 session_id char(30),
 secret char(30),
 expire_time double,
 primary key (user_id, session_id)
 )type=MyISAM;""")


 cursor.execute("alter table userSessions add index expire_time (expire_time);")

 cursor.execute("""create table links
 (
 source_pagename varchar(255),
 destination_pagename varchar(255),
 primary key (source_pagename, destination_pagename)
 ) type=InnoDB;""")

 cursor.execute("""create table events
 (
 uid mediumint primary key,
 event_time double,
 posted_by varchar(255),
 text mediumtext,
 location mediumtext,
 event_name mediumtext,
 posted_by_ip char(16),
 posted_time double 
 ) type=InnoDB;""")
 
 cursor.execute("alter table events add index event_time (event_time);")
 cursor.execute("alter table events add index posted_by (posted_by);")
 cursor.execute("alter table events add index posted_by_ip (posted_by_ip);")
 cursor.execute("alter table events add index posted_time (posted_time);")
 
 cursor.execute("""create table images
 (
 name varchar(255),
 image mediumblob,
 uploaded_time double,
 uploaded_by char(19),
 attached_to_pagename  varchar(255),
 uploaded_by_ip char(16),
 xsize smallint,
 ysize smallint,
 primary key (name, attached_to_pagename)
 ) type=InnoDB;""")
 
 cursor.execute("alter table images add index uploaded_by (uploaded_by);")
 cursor.execute("alter table images add index uploaded_time (uploaded_time);")
 
 cursor.execute("""create table oldImages
 (
 name varchar(255),
 image mediumblob,
 uploaded_time double,
 uploaded_by char(19),
 attached_to_pagename varchar(255),
 deleted_time double,
 deleted_by char(19),
 uploaded_by_ip char(16),
 deleted_by_ip char(16),
 primary key (name, attached_to_pagename, uploaded_time)
 ) type=InnoDB;""")
 
 cursor.execute("alter table oldImages add index deleted_time (deleted_time);")
 
 #throw-away and easily regenerated data
 cursor.execute("""create table thumbnails
 (              
 xsize smallint,
 ysize smallint,
 name varchar(255),
 attached_to_pagename varchar(255),
 image mediumblob,
 last_modified double,
 primary key (name, attached_to_pagename)
 ) type=MyISAM;""")

 cursor.execute("""create table imageCaptions
 (
  image_name varchar(255),
  attached_to_pagename varchar(255),
  linked_from_pagename varchar(255),
  caption text,
  primary key (image_name, attached_to_pagename, linked_from_pagename)
 ) type=InnoDB;""")

 cursor.execute("""create table mapChanges
 (
   pagename varchar(255),
   change_time double,
   changed_by char(19),
   changed_by_ip char(16),
   primary key (change_time)
 ) type=InnoDB;""")


def create_views(cursor):
 cursor.execute("CREATE VIEW eventChanges as SELECT 'Events Board' as name, events.posted_time as changeTime, users.id as id, 'NEWEVENT' as editType, events.event_name as comment, events.posted_by_IP as userIP from events, users where users.name=events.posted_by;")
 cursor.execute("CREATE VIEW deletedImageChanges as SELECT oldImages.attached_to_pagename as name, oldImages.deleted_time as changeTime, oldImages.deleted_by as id, 'ATTDEL' as editType, name as comment, oldImages.deleted_by_ip as userIP from oldImages;")
 cursor.execute("CREATE VIEW oldImageChanges as SELECT oldImages.attached_to_pagename as name, oldImages.uploaded_time as changeTime, oldImages.uploaded_by as id, 'ATTNEW' as editType, name as comment, oldImages.uploaded_by_ip as userIP from oldImages;")
 cursor.execute("CREATE VIEW currentImageChanges as SELECT images.attached_to_pagename as name, images.uploaded_time as changeTime, images.uploaded_by as id, 'ATTNEW' as editType, name as comment, images.uploaded_by_ip as userIP from images;")
 cursor.execute("CREATE VIEW pageChanges as SELECT name, editTime as changeTime, userEdited as id, editType, comment, userIP from allPages;")

def create_other_stuff(cursor):
 cursor.execute("INSERT into users set name='';")

def insert_basic_pages(cursor):
 cursor.execute("insert into curPages set name='Front Page', text='Edit me..This is the front page!', editTime=UNIX_TIMESTAMP('2005-11-09 14:44:00');")
 cursor.execute("insert into allPages set name='Front Page', text='Edit me..This is the front page!', editTime=UNIX_TIMESTAMP('2005-11-09 14:44:00'), editType='SAVENEW', comment='System page';")
 cursor.execute("insert into curPages set name='User Preferences', text=%s, editTime=UNIX_TIMESTAMP('2005-11-09 14:44:00');", (userpref_text))
 cursor.execute("insert into allPages set name='User Preferences', text=%s, editTime=UNIX_TIMESTAMP('2005-11-09 14:44:00'), editType='SAVENEW', comment='System page';", (userpref_text))
 
 cursor.execute("insert into curPages set name='Recent Changes', text=%s, editTime=UNIX_TIMESTAMP('2005-11-09 14:44:00');", (rc_text))
 cursor.execute("insert into allPages set name='Recent Changes', text=%s, editTime=UNIX_TIMESTAMP('2005-11-09 14:44:00'), editType='SAVENEW', comment='System page';", (rc_text))


db = wikidb.connect()
cursor = db.cursor()
cursor.execute("start transaction;")
create_tables(cursor)
create_views(cursor)
create_other_stuff(cursor)
insert_basic_pages(cursor)
cursor.execute("commit;")
db.close()
