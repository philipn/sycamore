# -*- coding: utf-8 -*-
"""
This script will rollback all edits made by a particular user OR IP that
occured at or after the time since_time_str.

The script does NOT take into account the fact that editors AFTER the evil
editor may have fixed the page.
We roll back to the prior version of the page no matter what.  In this sense,
we take a certain hit of stupidity, as good edits may have been made to the
vandalized pages after they were (presumably) reverted by wikipeople.

IN THE FUTURE, we should do this:
  0. Allow input of a set of usernames and IPs, rather than one.
  1. What's the prior, non-fucked version of this page?
  2. Has the page been reverted (SAVE/REVERT) to a prior version by a
     non-nasty user (or, in the case of a new page, has it been deleted)?
     If so, we don't touch the page.
     a. Or maybe, instead of "don't touch," we actually permanently nuke the
        versions in between-and-including the revert and the first
        stupid vesion.
  3. Otherwise, do what we do now.

Change the things in CHANGEME.
"""

# Imports
import sys
import time
import os

__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', 'share'))]),

import __init__
from Sycamore.Page import Page
from Sycamore.PageEditor import PageEditor
from Sycamore.action.revert import revert_to_page
from Sycamore.action import Files

from Sycamore import config
from Sycamore import request
from Sycamore import user
from Sycamore import wikiutil
from Sycamore import caching

req = request.RequestDummy()
cursor = req.cursor

##############################################################################
# CHANGEME:
##############################################################################
since_time_str = '2007-05-06 12:10:26' # Y-M-D HH:MM:SS in LOCAL MACHINE
# TIME ZONE, NOT UTC (unless machine is in local UTC time)
# 'date' command in unix will tell you your local machine timezone.
##############################################################################
# We do an OR of username and user_ip
##############################################################################
username = 'philiptest'
user_ip = None
##############################################################################

since_time = time.mktime(time.strptime(since_time_str,
                                       '%Y-%m-%d %H:%M:%S')) - 1

# TODO: use time.mktime(time.strptime('2007-04-16 20:40:41',...
d = {'username': username, 'since_time': since_time, 'user_ip': user_ip}

def get_least_recently_edited_pages(d, request):
     def get_page_right_before(results):
         right_before = []
         for name, version_date, wiki_name in results:
                d['resultname'] = name
                d['resultversion'] = version_date
                d['resultwiki'] = wiki_name
                request.cursor.execute("""SELECT editTime from allPages, wikis
                    where allPages.name=%(resultname)s and
                          editTime < %(resultversion)s and
                          wikis.name=%(resultwiki)s and
                          allPages.wiki_id=wikis.id
                    order by editTime desc limit 1""", d)
                result = request.cursor.fetchone()
                version = None
                if result:
                    version = result[0]
                right_before.append((name, version, wiki_name))
         return right_before

     least_recently_edited = {}
     if d['username']:
            # get the version of the page right before this user fucked it up.
            request.cursor.execute("""
                SELECT allPages.name, min(allPages.editTime), wikis.name
                from allPages, users, wikis
                where allPages.userEdited=users.id and
                      users.name=%(username)s and
                      allPages.editTime >= %(since_time)s and
                      wikis.id=allPages.wiki_id
                group by allPages.name, wikis.name""", d)
            right_before = get_page_right_before(request.cursor.fetchall()) 
            for name, version_date, wiki_name in right_before:
                least_recently_edited[(name, wiki_name)] = version_date
     if d['user_ip']:
            # get the version of the page right before this IP-user fucked
            # it up.
            request.cursor.execute("""
                SELECT allPages.name, min(allPages.editTime), wikis.name
                from allPages, wikis
                where allPages.userIP=%(user_ip)s and
                      allPages.editTime >= %(since_time)s and
                      wikis.id=allPages.wiki_id
                group by allPages.name, wikis.name""", d)
            right_before = get_page_right_before(request.cursor.fetchall()) 
            for name, version_date, wiki_name in right_before:
                if (name, wiki_name) in least_recently_edited:
                    if version_date < least_recently_edited[(name, wiki_name)]:
                        least_recently_edited[(name, wiki_name)] = version_date
                else:
                    least_recently_edited[(name, wiki_name)] = version_date

     return least_recently_edited

def get_prior_file_versions(d, request):
    def get_file_right_before(results):
         right_before = []
         for name, attached_to_pagename, version_date, wiki_name in results:
            d['resultname'] = name
            d['resultpagename'] = attached_to_pagename
            d['resultversion'] = version_date
            d['resultwiki'] = wiki_name
            request.cursor.execute("""
                SELECT uploaded_time from oldFiles, wikis
                    where oldFiles.name=%(resultname)s and
                          oldFiles.attached_to_pagename=%(resultpagename)s and
                          uploaded_time < %(resultversion)s and
                          wikis.name=%(resultwiki)s and
                          oldFiles.wiki_id=wikis.id
                    order by uploaded_time desc limit 1""", d)
            result = request.cursor.fetchone()
            if result:
                version = result[0]
                right_before.append((name, attached_to_pagename, version,
                                     wiki_name))
         return right_before

    def set_prior_file_versions(results, current=False, deleted_by_user=False):
        for name, attached_to_pagename, uploaded_time, wiki_name in results:
            file_id = (name, attached_to_pagename, wiki_name)
            if ((name, attached_to_pagename, wiki_name) not in
                prior_file_versions):
                prior_file_versions[file_id] = (uploaded_time, current,
                                                deleted_by_user)
            elif (uploaded_time < prior_file_versions[file_id][0] or
                 (deleted_by_user and
                  uploaded_time == prior_file_versions[file_id][0])):
                prior_file_versions[file_id] = (uploaded_time, current,
                                                deleted_by_user)

    prior_file_versions = {}
    if d['username']:
        # get the version of the file right before this user fucked it up.
        request.cursor.execute("""SELECT oldFiles.name,
            oldFiles.attached_to_pagename, min(oldFiles.uploaded_time),
            wikis.name from oldFiles, users, wikis
            where oldFiles.uploaded_by=users.id and
                  users.name=%(username)s and
                  oldFiles.uploaded_time >= %(since_time)s and
                  wikis.id=oldFiles.wiki_id
            group by oldFiles.name, oldFiles.attached_to_pagename,
                     wikis.name""", d, isWrite=True)
        right_before = get_file_right_before(request.cursor.fetchall())
        set_prior_file_versions(right_before, current=False)

        # check to see if the user deleted the file.  what a jerk!
        request.cursor.execute("""SELECT del.name, del.attached_to_pagename,
            oldFiles.uploaded_time, del.wiki_name from
                (SELECT oldFiles.name as name,
                        oldFiles.attached_to_pagename as attached_to_pagename,
                        min(oldFiles.deleted_time) as deleted_time,
                        wikis.name as wiki_name
                 from oldFiles, users, wikis
                 where oldFiles.deleted_by=users.id and
                       users.name=%(username)s and
                       oldFiles.deleted_time >= %(since_time)s and
                       wikis.id=oldFiles.wiki_id
                 group by oldFiles.name, oldFiles.attached_to_pagename,
                          wikis.name
                ) as del,
                oldFiles, wikis
            where oldFiles.name=del.name and
                  oldFiles.attached_to_pagename=del.attached_to_pagename and
                  oldFiles.deleted_time=del.deleted_time and
                  wikis.name=del.wiki_name and oldFiles.wiki_id=wikis.id""",
            d, isWrite=True)
        set_prior_file_versions(request.cursor.fetchall(), current=False,
                                deleted_by_user=True)
       
        # get the version of the file right before this user fucked it up.
        request.cursor.execute("""SELECT files.name,
            files.attached_to_pagename, files.uploaded_time, wikis.name
            from files, users, wikis
            where files.uploaded_by=users.id and users.name=%(username)s and
                  files.uploaded_time >= %(since_time)s and
                  wikis.id=files.wiki_id""", d, isWrite=True)

        current_files = request.cursor.fetchall()
        set_prior_file_versions(current_files, current=True)

        right_before = get_file_right_before(current_files)
        set_prior_file_versions(right_before)
        
    if d['user_ip']:
        # get the version of the file right before this user-IP fucked it up.
        request.cursor.execute("""SELECT oldFiles.name,
            oldFiles.attached_to_pagename, min(oldFiles.uploaded_time),
            wikis.name
            from oldFiles, wikis
            where oldFiles.uploaded_by_ip=%(user_ip)s and
                  oldFiles.uploaded_time >= %(since_time)s and
                  wikis.id=oldFiles.wiki_id
            group by oldFiles.name, oldFiles.attached_to_pagename,
                     wikis.name""", d, isWrite=True)
        right_before = get_file_right_before(request.cursor.fetchall())
        set_prior_file_versions(right_before, current=False)

        # check to see if the user-IP deleted the file.  what a jerk!
        request.cursor.execute("""SELECT del.name, del.attached_to_pagename,
            oldFiles.uploaded_time, del.wiki_name from (
                SELECT oldFiles.name as name,
                       oldFiles.attached_to_pagename as attached_to_pagename,
                       min(oldFiles.deleted_time) as deleted_time,
                       wikis.name as wiki_name
                from oldFiles, wikis
                where oldFiles.deleted_by_ip=%(user_ip)s and
                      oldFiles.deleted_time >= %(since_time)s and
                      wikis.id=oldFiles.wiki_id
                group by oldFiles.name, oldFiles.attached_to_pagename,
                         wikis.name
                ) as del,
                oldFiles, wikis
            where oldFiles.name=del.name and
                  oldFiles.attached_to_pagename=del.attached_to_pagename and
                  oldFiles.deleted_time=del.deleted_time and
                  wikis.name=del.wiki_name and
                  oldFiles.wiki_id=wikis.id""", d, isWrite=True)
        set_prior_file_versions(request.cursor.fetchall(), current=False,
                                deleted_by_user=True)

        # get the version of the file right before this user-IP fucked it up.
        request.cursor.execute("""SELECT files.name,
            files.attached_to_pagename, files.uploaded_time, wikis.name
            from files, wikis
            where files.uploaded_by_ip=%(user_ip)s and
                  files.uploaded_time >= %(since_time)s and
                  wikis.id=files.wiki_id""", d, isWrite=True)
        current_files = request.cursor.fetchall()
        set_prior_file_versions(current_files, current=True)

        right_before = get_file_right_before(current_files)
        set_prior_file_versions(right_before)

    return prior_file_versions

def revert_page_to_version(pagename, wiki_name, version_date, request):
    request.switch_wiki(wiki_name)
    pg = PageEditor(pagename, request)
    oldpg = Page(pagename, request, prev_date=version_date)
    revert_to_page(oldpg, request, pg, permanent=True, showrc=False)

def delete_page(pagename, wiki_name, request):
    request.switch_wiki(wiki_name)
    pg = PageEditor(pagename, request)
    pg.deletePage('', permanent=True, showrc=False)

def delete_file(filename, pagename, wiki_name, request):
    request.switch_wiki(wiki_name)
    Files.del_file(filename, pagename, request, permanent=True)

def revert_file_to_version(filename, pagename, version_date, wiki_name,
                           request, keep_deleted_state=False):
    request.switch_wiki(wiki_name)
    Files.restore_file(filename, version_date, pagename, request,
                       permanent=True, showrc=False,
                       keep_deleted_state=keep_deleted_state)

if __name__ == '__main__':
    least_recently_edited_pages = get_least_recently_edited_pages(d, req)
    for (pagename, wiki_name) in least_recently_edited_pages:
        version_date = least_recently_edited_pages[(pagename, wiki_name)]
        if version_date is not None:
            revert_page_to_version(pagename, wiki_name, version_date, req)
        else:
            delete_page(pagename, wiki_name, req)

    prior_file_versions = get_prior_file_versions(d, req)
    for (filename, pagename, wiki_name) in prior_file_versions:
        file_id = (filename, pagename, wiki_name)
        version_date, current, deleted_by_user = prior_file_versions[file_id]
        if current:
            # no prior version
            delete_file(filename, pagename, wiki_name, req)
        else:
            revert_file_to_version(filename, pagename, version_date,
                                   wiki_name, req,
                                   keep_deleted_state=(not deleted_by_user))
    req.db_disconnect()
