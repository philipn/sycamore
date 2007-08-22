"""
Converts over the wiki to allow for user page change notification.
"""

# Imports
import sys
import cStringIO
import os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__,
                                              '..', '..','..'))])
from Sycamore import config
from Sycamore import request
from Sycamore import wikidb
from Sycamore import user
from Sycamore import wikiutil
from Sycamore.Page import Page

def getAllCurrentPages(req):
    req.cursor.execute("""SELECT curPages.name, wikis.name from curPages, wikis where curPages.wiki_id=wikis.id""")
    return req.cursor.fetchall()

req = request.RequestDummy()
wiki_list = wikiutil.getWikiList(req)

if config.db_type == 'mysql':
    req.cursor.execute("""create table userPageOnWikis
    (
    username varchar(100) not null,
    wiki_name varchar(100) not null,
    primary key (username, wiki_name)
    ) ENGINE=InnoDB CHARACTER SET utf8;""", isWrite=True)
elif config.db_type == 'postgres':
    req.cursor.execute("""create table userPageOnWikis
    (
    username varchar(100) not null,
    wiki_name varchar(100) not null,
    primary key (username, wiki_name)
    );""", isWrite=True)

req.cursor.execute("""CREATE INDEX userPageOnWikis_username on
    userPageOnWikis (username);""", isWrite=True)

userpages = {}
for pagename, wiki_name in getAllCurrentPages(req):
    if pagename.startswith(config.user_page_prefix.lower()):
        username = pagename[len(config.user_page_prefix):].lower()
        if userpages.has_key(username):
            userpages[username].append(wiki_name)
        else:
            userpages[username] = [wiki_name]

for username in userpages:
    the_user = user.User(req, name=username)
    for wiki_name in userpages[username]:
        d = {'wiki_name': wiki_name, 'username': username}
        req.cursor.execute(
            """INSERT INTO userPageOnWikis (username, wiki_name)
               VALUES (%(username)s, %(wiki_name)s)""", d, isWrite=True)
        # add to user's bookmarks, if it's not already there
        user_page = Page(config.user_page_prefix + the_user.name, req,
                         wiki_name=wiki_name)
        if not the_user.isFavoritedTo(user_page):
            the_user.favoritePage(user_page)

req.db_disconnect()
