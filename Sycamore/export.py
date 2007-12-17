# -*- coding: utf-8 -*-
"""
Export a wiki.  Note that some sections will appear in the export
only if you have permission.  The security section, for instance,
will appear only if you are an administrator of the wiki in question.

Export format looks something like:

<sycamore version="0.1d">
<wiki name="shortname" id="wiki_id" domain="domain name"
      is_disabled="True / False" sitename="long site name">
<settings key="value" ../>
<pages>
<page name="page name" propercased_name="Page Name">
<text>current page text</text>
<version propercased_name="Page Name!" edit_time="unix tm"
         user_edited="username" edit_type="an enum edit type str"
         comment="edit comment" user_ip="ip of edit">
<text>this version page text</text>
</version>
</page>
</pages>

<files>
<file name="filename" attached_to_pagename="page name">
      uploaded_time="unix tm" uploaded_by="username"
      uploaded_by_ip="ip addr"
      attached_to_pagename_propercased="Page Name"
      deleted="False">base64 encoded file content</file>
<file name="filename" attached_to_pagename="page name">
      uploaded_time="unix tm" uploaded_by="username"
      uploaded_by_ip="ip addr"
      deleted_time="unix tm" deleted_by="username"
      deleted_by_ip="ip addr"
      attached_to_pagename_propercased="Page Name"
      deleted="True">base 64 encoded file content</file>
...
</files>

<events>
<event event_time="unix tm" posted_by="username" location="text here"
       name="name of event" posted_by_ip="ip addr"
       posted_time="unix tm">event text</event>
</events>

<security>
<acls>
<acl pagename="page name" groupname="group name"
     may_read="True / False" may_edit="True / False"
     may_delete="True / False" may_admin="True / False" />
...
</acls>
<groups>
<group name="group name">
<defaults may_read="True / False" may_edit="True / False"
          may_delete="True / False"    may_admin="True / False" />
<user="user name"/>
<user="user name2"/>
<user="ip addr" type="IP">
..
</group>
</groups>
</security>

<map>
<current>
<point pagename="page name" x="x loc" y="y loc"
       created_time="unix tm" created_by="user name"
       created_by_ip="ip addr" pagename_propercased="page Name"
       address="address string" />
...
</current>
<old>
<point pagename="page name" x="x loc" y="y loc"
       created_time="unix tm" created_by="user name"
       created_by_ip="ip addr"
       deleted_time="unix tm" deleted_by="username"
       deleted_by_ip="ip addr"
       pagename_propercased="page Name"
       address="address string" />
...
</old>
</map>
</wiki>
</sycamore>
"""

# Imports
import sys
import os
import shutil
import time
import xml.dom.minidom
from xml.dom.minidom import getDOMImplementation
from base64 import b64encode
from copy import copy

import __init__ # woo hackmagic
__directory__ = os.path.dirname(__file__)
share_directory = os.path.abspath(
    os.path.join(__directory__, '..', 'share'))
sys.path.extend([share_directory])

from Sycamore import config
from Sycamore import wikiutil
from Sycamore import request
from Sycamore import user
from Sycamore import wikiacl
from Sycamore import wikidb
from Sycamore.Page import Page
from Sycamore import __version__
from Sycamore.wikiutil import quoteFilename, unquoteFilename
from Sycamore.action import Files

xml = getDOMImplementation()
dummy_name = "attrs"
command_line = False

def getPageList(request, objects=True):
    """
    Generate a "master" pagelist of all pages that have
    ever existed!
    """
    request.cursor.execute(
        """SELECT name FROM allPages
           WHERE wiki_id=%(wiki_id)s
           GROUP BY name""", {'wiki_id': request.config.wiki_id})
    page_list = []
    for result in request.cursor.fetchall():
        page_name = result[0] 
        if objects:
            page_list.append(Page(page_name, request))
        else:
            page_list.append(page_name)
    return page_list

def generate_attributes(dict):
    """
    Given a dictionary we create a string of XML-y attributes.
    """
    doc = xml.createDocument(None, dummy_name, None)
    root = doc.documentElement
    for key, value in dict.iteritems():
        if type(value) is str:
            value = value.decode(config.charset)
        elif value is None:
            value = ''
        elif type(value) is not unicode:
            value = str(value).decode(config.charset)
        root.setAttribute(key, value)

    return root.toxml()[len(dummy_name)+2:-2].encode(config.charset)

def get_username(user_id, request):
    """
    Return username given user_id.

    user_id may also be the 'anon:' format.
    """
    if not user_id or user_id.startswith('anon'):
        return None
    return user.User(request, id=user_id).propercased_name

def start_wiki(request, file):
    d = {
        'name': request.config.wiki_name,
        'id': request.config.wiki_id,
        'domain': request.config.domain,
        'is_disabled': request.config.is_disabled,
        'sitename': request.config.sitename
    }
    text = '<wiki %s>\n' % generate_attributes(d)
    file.write(text)

def wiki_settings(request, file):
    local_config = config.reduce_to_local_config(
        request.config.__dict__)
    file.write('<settings %s />\n' %
               generate_attributes(local_config))

def start_pages(request, file):
    file.write('<pages>\n')

def get_page_text(page, file):
    doc = xml.createDocument(None, "text", None)
    root = doc.documentElement
    text = doc.createTextNode(page.get_raw_body(fresh=True))
    root.appendChild(text)
    file.write(root.toxml().encode(config.charset) + '\n')

def get_versions(page, file):
    """
    Write the text for all the versions of the page.
    """
    page.request.cursor.execute(
      """SELECT propercased_name, editTime, userEdited, editType,
                comment, userIP
         from allPages
         where name=%(pagename)s and wiki_id=%(wiki_id)s
         order by editTime desc""",
      {'pagename':page.page_name, 'wiki_id':page.wiki_id})

    for result in page.request.cursor.fetchall():
        d = {'propercased_name': result[0],
             'edit_time': result[1],
             'user_edited': get_username(result[2], page.request),
             'edit_type': result[3].strip(),
             'comment': result[4],
             'user_ip': result[5]
        }
        file.write('<version %s>\n' % generate_attributes(d))
        version = Page(page.page_name, page.request,
                            prev_date=d['edit_time'])
        get_page_text(version, file)
        file.write('</version>\n')

def pages(request, file):
    """
    Export the pages that are viewable to us.
    """
    start_pages(request, file)
    for page in getPageList(request, objects=True):
        if (not command_line and
            not request.user.may.read(page)):
           continue 
        d = {'name': page.page_name,
             'propercased_name': page.proper_name()}
        file.write('<page %s>' % generate_attributes(d))

        get_page_text(page, file)
        get_versions(page, file)

        file.write('</page>\n')
    end_pages(request, file)

def end_pages(request, file):
    file.write('</pages>\n')

def end_wiki(request, file):
    file.write("</wiki>\n")

def start_files(request, file):
    file.write('<files>\n')

def end_files(request, file):
    file.write('</files>\n')

def start_file(d, request, file):
    file.write('<file %s>' % generate_attributes(d))

def end_file(d, request, file):
    file.write('</file>\n')

def file_content(file_attrs, request, output, deleted=False):
    d = {'filename': file_attrs['name'],
         'page_name': file_attrs['attached_to_pagename']}
    if deleted:
        version = file_attrs['uploaded_time']
        d['file_version'] = version
        file = wikidb.getFile(request, d, deleted=True,
                              version=version, fresh=True)
    else:
        file = wikidb.getFile(request, d, fresh=True)
    file_str = file[0]

    base64_file_str = b64encode(file_str)
    doc = xml.createDocument(None, dummy_name, None)
    root = doc.documentElement
    text = doc.createTextNode(base64_file_str)
    output.write(text.toxml())

def list_current_files(page):
    page.request.cursor.execute(
        """SELECT name, uploaded_time, uploaded_by, uploaded_by_ip,
                  attached_to_pagename_propercased
           from files
           where attached_to_pagename=%(attached_to_pagename)s
                 and wiki_id=%(wiki_id)s""",
        {'wiki_id': page.wiki_id,
         'attached_to_pagename': page.page_name})
    return page.request.cursor.fetchall()

def files_current_versions(page, file_attrs, file):
    """
    Get current file versions.
    """
    for result in list_current_files(page):
        file_attrs['name'] = result[0]
        file_attrs['uploaded_time'] = result[1]
        file_attrs['uploaded_by'] = get_username(
            result[2], page.request)
        file_attrs['uploaded_by_ip'] = result[3]
        file_attrs['attached_to_pagename_propercased'] = result[4]
        file_attrs['deleted'] = False

        if file_attrs.has_key('wiki_id'):
            del file_attrs['wiki_id'] # don't want to write it

        start_file(file_attrs, page.request, file)
        file_content(file_attrs, page.request, file)
        end_file(file_attrs, page.request, file)

def list_old_files(page):
    page.request.cursor.execute(
        """SELECT name, uploaded_time, uploaded_by, uploaded_by_ip,
                  deleted_time, deleted_by, deleted_by_ip,
                  attached_to_pagename_propercased
           from oldFiles 
           where attached_to_pagename=%(attached_to_pagename)s
                 and wiki_id=%(wiki_id)s""",
        {'attached_to_pagename': page.page_name,
         'wiki_id': page.wiki_id})
    return page.request.cursor.fetchall()

def files_old_versions(page, file_attrs, file):
    """
    Get old file versions.
    """
    for result in list_old_files(page):
        file_attrs['name'] = result[0]
        file_attrs['uploaded_time'] = result[1]
        file_attrs['uploaded_by'] = get_username(
            result[2], page.request)
        file_attrs['uploaded_by_ip'] = result[3]
        file_attrs['deleted_time'] = result[4]
        file_attrs['deleted_by'] = get_username(
            result[5], page.request)
        file_attrs['deleted_by_ip'] = result[5]
        file_attrs['attached_to_pagename_propercased'] = result[6]
        file_attrs['deleted'] = True

        if file_attrs.has_key('wiki_id'):
            del file_attrs['wiki_id'] # don't want to write it

        start_file(file_attrs, page.request, file)
        file_content(file_attrs, page.request, file, deleted=True)
        end_file(file_attrs, page.request, file)

def files(request, file):
    """
    Export the files (and past versions) of files on pages
    we are allowed to view.
    """
    start_files(request, file)
    for page in getPageList(request, objects=True):
        if (not command_line and
            not request.user.may.read(page)):
           continue 
        in_file = False
        d = {'attached_to_pagename': page.page_name,
             'wiki_id': page.wiki_id}

        files_current_versions(page, d, file)
        files_old_versions(page, d, file)

    end_files(request, file)

def start_events(request, file):
    file.write('<events>\n')

def end_events(request, file):
    file.write('</events>\n')

def events(request, file):
    """
    Export all of the events data.
    """
    events_page = Page('Events Board', request)
    if (not command_line and
        not request.user.may.read(events_page)):
        return
    start_events(request, file)
    request.cursor.execute(
        """SELECT event_time, posted_by, location, event_name,
                  posted_by_ip, posted_time, text
           FROM events WHERE wiki_id=%(wiki_id)s""",
        {'wiki_id': request.config.wiki_id})
    for result in request.cursor.fetchall():
        d = {'event_time': result[0],
             'posted_by': result[1],
             'location': result[2],
             'event_name': result[3],
             'posted_by_ip': result[4],
             'posted_time': result[5]}
        text = result[6]

        file.write('<event %s>' % generate_attributes(d))
        file.write(text)
        file.write('</event>\n')
        
    end_events(request, file)

def start_security(request, file):
    file.write('<security>\n')

def end_security(request, file):
    file.write('</security>\n')

def acls(request, file):
    for page in getPageList(request, objects=True):
        acl = page.getACL()
        if acl.default_acl:
            continue

        for groupname, privs in acl.acl_dict.iteritems():
            d = {'pagename': page.page_name, 'groupname': groupname,
                 'may_read': privs[0], 'may_edit': privs[1],
                 'may_delete': privs[2], 'may_admin': privs[3]}
            file.write('<acl %s />\n' % generate_attributes(d)) 

def group_defaults(group, request, file):
    read, edit, delete, admin = group.default_rights()
    defaults = {'may_read': read,
                'may_edit': edit,
                'may_delete': delete,
                'may_admin': admin}
    file.write('<defaults %s />\n' % generate_attributes(defaults))
     
def groups(request, file):
    file.write('<groups>\n')
    group_list = user.getGroupList(request)
    for groupname in group_list:
        group = wikiacl.Group(groupname, request, fresh=True)
        file.write('<group %s>\n' %
                   generate_attributes({'name': groupname}))
        group_defaults(group, request, file)
        for username in group.users():
            file.write('<%s/>\n' % generate_attributes(
                                    {'user': username}))
        for ip in group.get_ips().keys():
            file.write('<%s/>\n' % generate_attributes(
                                    {'user': username,
                                     'type': 'IP'}))
            
        file.write('</group>\n')
    file.write('</groups>\n')

def security(request, file):
    if (not command_line and
        not request.user.name in wikiacl.Group("Admin", request)):
        return

    start_security(request, file)
    acls(request,file)
    groups(request,file)
    end_security(request, file)

def start_map(request, file):
    file.write('<map>\n')

def end_map(request, file):
    file.write('</map>\n')

def map(request, file):
    start_map(request, file)
    file.write('<current>\n')
    for page in wikiutil.getPageList(request, objects=True):
        if (not command_line and
            not request.user.may.read(page)):    
            continue
        request.cursor.execute(
            """SELECT x, y, created_time, created_by, created_by_ip,
                      pagename_propercased, address
               FROM mapPoints
               WHERE wiki_id=%(wiki_id)s AND
                     pagename=%(pagename)s""",
            {'wiki_id': page.wiki_id, 'pagename': page.page_name})
        for mapitem in request.cursor.fetchall():
            d = {'pagename': page.page_name, 'x': mapitem[0],
                 'y': mapitem[1], 'created_time': mapitem[2],
                 'created_by': get_username(mapitem[3], request),
                 'created_by_ip': mapitem[4],
                 'pagename_propercased': mapitem[5],
                 'address': mapitem[6]}
            file.write('<point %s />\n' % generate_attributes(d))
    file.write('</current>\n')
    file.write('<old>\n')
    for page in wikiutil.getPageList(request, objects=True):
        if (not command_line and
            not request.user.may.read(page)):    
            continue

        request.cursor.execute(
            """SELECT x, y, created_time, created_by, created_by_ip,
                      pagename_propercased, address,
                      deleted_time, deleted_by, deleted_by_ip
               FROM oldMapPoints
               WHERE wiki_id=%(wiki_id)s AND
                     pagename=%(pagename)s""",
            {'wiki_id': page.wiki_id, 'pagename': page.page_name})
        for mapitem in request.cursor.fetchall():
            d = {'pagename': page.page_name, 'x': mapitem[0],
                 'y': mapitem[1], 'created_time': mapitem[2],
                 'created_by': get_username(mapitem[3], request),
                 'created_by_ip': mapitem[4],
                 'pagename_propercased': mapitem[5],
                 'address': mapitem[6], 'deleted_time': mapitem[7],
                 'deleted_by': mapitem[8],
                 'deleted_by_ip': get_username(mapitem[9], request)}
            file.write('<point %s />\n' % generate_attributes(d))
    file.write('</old>\n')

    end_map(request, file)

def export(request, wiki_name=None):
    """
    We do this in chunks because loading an entire wiki into memory
    is kinda a bad idea.
    """
    if not wiki_name:
        # TODO: full export
        return
    f = open('%s.%s.wiki.xml' % (wiki_name, time.time()), 'w')

    xml_header = ('<?xml version="1.0" ?>\n'
                  '<sycamore>\n')
    xml_footer = '</sycamore>'
    f.write(xml_header)

    start_wiki(request, f)
    wiki_settings(request, f)

    pages(request, f)
    files(request, f)
    events(request, f)
    security(request, f)
    map(request, f)

    end_wiki(request, f)
    f.write(xml_footer)
    f.close()

if __name__ == '__main__':
    command_line = True

    sys.stdout.write("Enter the wiki shortname: ")
    wiki_name = raw_input().strip().lower()

    req = request.RequestDummy(wiki_name=wiki_name)

    print "  1) Admin grab -- everything no matter what"
    print "  2) Unprivileged user grab -- only what non-logged in"
    print "     public can see."
    grab_level = raw_input().strip()
    if grab_level == '2':
        request.user = user.User(req)

    export(req, wiki_name=wiki_name)
    req.db_disconnect()
