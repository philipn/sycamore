import sys, cStringIO, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..'))])

from Sycamore import wikiutil, config, request, caching, wikidb, maintenance, buildDB
from Sycamore.Page import Page
from Sycamore.buildDB import FlatPage

req = request.RequestDummy()
cursor = req.cursor
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

cursor.execute("CREATE INDEX files_uploaded_by on files (uploaded_by);", isWrite=True)
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
  ) ENGINE=InnoDB CHARACTER SET utf8;""")
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
  );""")

if config.db_type == 'mysql':
   cursor.execute("""create table imageInfo
   (
   name varchar(100) not null,
   attached_to_pagename varchar(255) not null,
   xsize smallint,
   ysize smallint,
   primary key (name, attached_to_pagename)
   ) ENGINE=InnoDB CHARACTER SET utf8;""")
elif config.db_type == 'postgres':
   cursor.execute("""create table imageInfo
   (
   name varchar(100) not null,
   attached_to_pagename varchar(255) not null,
   xsize smallint,
   ysize smallint,
   primary key (name, attached_to_pagename)
   );""")

if config.db_type == 'mysql':
   cursor.execute("""create table oldImageInfo
   (
   name varchar(100) not null,
   attached_to_pagename varchar(255) not null,
   xsize smallint,
   ysize smallint,
   uploaded_time double not null,
   primary key (name, attached_to_pagename, uploaded_time)
   ) ENGINE=InnoDB CHARACTER SET utf8;""")
elif config.db_type == 'postgres':
   cursor.execute("""create table oldImageInfo
   (
   name varchar(100) not null,
   attached_to_pagename varchar(255) not null,
   xsize smallint,
   ysize smallint,
   uploaded_time double precision not null,
   primary key (name, attached_to_pagename, uploaded_time)
   );""")

cursor.execute("CREATE INDEX oldFiles_deleted_time on oldFiles (deleted_time);")

# views
cursor.execute("CREATE VIEW deletedFileChanges as SELECT oldFiles.attached_to_pagename as name, oldFiles.deleted_time as changeTime, oldFiles.deleted_by as id, 'ATTDEL' as editType, name as comment, oldFiles.deleted_by_ip as userIP, oldFiles.attached_to_pagename_propercased as propercased_name from oldFiles;")
cursor.execute("CREATE VIEW oldFileChanges as SELECT oldFiles.attached_to_pagename as name, oldFiles.uploaded_time as changeTime, oldFiles.uploaded_by as id, 'ATTNEW' as editType, name as comment, oldFiles.uploaded_by_ip as userIP, oldFiles.attached_to_pagename_propercased as propercased_name from oldFiles;")
cursor.execute("CREATE VIEW currentFileChanges as SELECT files.attached_to_pagename as name, files.uploaded_time as changeTime, files.uploaded_by as id, 'ATTNEW' as editType, name as comment, files.uploaded_by_ip as userIP, files.attached_to_pagename_propercased as propercased_name from files;")

cursor.execute("SELECT name, image, uploaded_time, uploaded_by, attached_to_pagename, uploaded_by_ip, attached_to_pagename_propercased, xsize, ysize from images")
results = cursor.fetchall()
for result in results:
    image_dict = { 'name': result[0], 'image': result[1], 'uploaded_time': result[2], 'uploaded_by': result[3], 'attached_to_pagename': result[4], 'uploaded_by_ip': result[5], 'attached_to_pagename_propercased': result[6], 'xsize': result[7], 'ysize': result[8] }
    cursor.execute("INSERT into files (name, file, uploaded_time, uploaded_by, attached_to_pagename, uploaded_by_ip, attached_to_pagename_propercased) values (%(name)s, %(image)s, %(uploaded_time)s, %(uploaded_by)s, %(attached_to_pagename)s, %(uploaded_by_ip)s, %(attached_to_pagename_propercased)s)", image_dict, isWrite=True)
    cursor.execute("INSERT into imageInfo (name, attached_to_pagename, xsize, ysize) values (%(name)s, %(attached_to_pagename)s, %(xsize)s, %(ysize)s)", image_dict, isWrite=True)

cursor.execute("SELECT name, attached_to_pagename, image, uploaded_by, uploaded_time, deleted_time, deleted_by, uploaded_by_ip, deleted_by_ip, attached_to_pagename_propercased, xsize, ysize from oldImages")
results = cursor.fetchall()
for result in results:
    oldimage_dict = { 'name': result[0], 'attached_to_pagename': result[1], 'image': result[2], 'uploaded_by': result[3], 'uploaded_time': result[4], 'deleted_time': result[5], 'deleted_by': result[6], 'uploaded_by_ip': result[7], 'deleted_by_ip': result[8], 'attached_to_pagename_propercased': result[9], 'xsize': result[10], 'ysize': result[11] }
    cursor.execute("INSERT into oldFiles (name, attached_to_pagename, file, uploaded_by, uploaded_time, deleted_time, deleted_by, uploaded_by_ip, deleted_by_ip, attached_to_pagename_propercased) values (%(name)s, %(attached_to_pagename)s, %(image)s, %(uploaded_by)s, %(uploaded_time)s, %(deleted_time)s, %(deleted_by)s, %(uploaded_by_ip)s, %(deleted_by_ip)s, %(attached_to_pagename_propercased)s)", oldimage_dict, isWrite=True)
    cursor.execute("INSERT into oldImageInfo (name, attached_to_pagename, xsize, ysize, uploaded_time) values (%(name)s, %(attached_to_pagename)s, %(xsize)s, %(ysize)s, %(uploaded_time)s)", oldimage_dict, isWrite=True)

# remove old views
cursor.execute("DROP VIEW deletedImageChanges")
cursor.execute("DROP VIEW oldImageChanges")
cursor.execute("DROP VIEW currentImageChanges")

# remove the old tables
cursor.execute("DROP TABLE images")
cursor.execute("DROP TABLE oldImages")

# get current theme information
theme_location = os.path.join(config.web_root, config.url_prefix[1:], config.theme_default)
css_location = os.path.join(theme_location, "css")
img_location = os.path.join(theme_location, "img")

screen_file = open(os.path.join(css_location, 'screen.css'))
screen_css = ''.join(screen_file.readlines())
screen_file.close()
common_file = open(os.path.join(css_location, 'common.css'))
common_css = ''.join(common_file.readlines())
common_file.close()
print_file = open(os.path.join(css_location, 'print.css'))
print_css = ''.join(print_file.readlines())
print_file.close()

logo_background_file = open(os.path.join(img_location, 'floater.png'))
logo_background = ''.join(logo_background_file.readlines())
logo_background_file.close()
if config.image_logo:
  logo_file = open(os.path.join(config.web_root, config.url_prefix[1:], config.image_logo))
  logo = ''.join(logo_file.readlines())
  logo_background_file.close()


flat_page_dict = { 'Wiki Settings': buildDB.basic_pages['Wiki Settings'],
'Wiki Settings/CSS': buildDB.basic_pages['Wiki Settings/CSS'],
'Wiki Settings/Images': buildDB.basic_pages['Wiki Settings/Images'] }

flat_page_dict['Wiki Settings/CSS'].files = [ ("screen.css", screen_css), ("common.css", common_css), ("print.css", print_css) ]
images_list = [ ("logo_background.png", logo_background) ]
if config.image_logo: images_list.append(("logo.png", logo))
flat_page_dict['Wiki Settings/Images'].files = images_list

buildDB.insert_pages(cursor, flat_page_dict)

plist = wikiutil.getPageList(req)
maintenance.buildCaches(plist)

req.db_disconnect()
