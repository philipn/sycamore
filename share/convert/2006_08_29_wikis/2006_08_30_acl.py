import sys, cStringIO, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])

from Sycamore import wikiutil, config, request, caching, wikidb, maintenance, buildDB, wikiacl
from Sycamore.Page import Page
from Sycamore.buildDB import FlatPage

wiki_name = 'anthill' # leave None if you aren't dealing with more than one wiki

admin_group = 'AdminGroup'  # the name of the old-style group who had admin-y rights
banned_group = 'BannedGroup' # the name of the old-style group who was banned
defined_user_groups = []

group_changed_message = """'''Note that these "group" pages are not how user groups are defined any more.  To define user groups, go into Wiki Settings/Security !'''"""

def parseACL(text):
    groupdict = None
    lines = text.split(' ')
    if lines: groupdict = {}
    for line in lines:
        line = line.strip()
        if not line: continue
        groupname = line[:line.find(':')]
        if groupname == admin_group:
          groupname = 'Admin'
        elif groupname == banned_group:
          groupname = 'Banned'
        else:
          if groupname != 'All' and groupname != 'Known' and groupname != 'Trusted': 
            if groupname not in defined_user_groups:
              defined_user_groups.append(groupname)
        rights = line[line.find(':')+1:].split(',')
        for right in rights:
            if right == 'none':
              groupdict[groupname] = [False, False, False, False]
              break
            elif right == 'write': right = 'edit'
            elif right == 'revert': continue

            if not groupdict.has_key(groupname):
                groupdict[groupname] = [False, False, False, False]
            groupdict[groupname][wikiacl.ACL_RIGHTS_TABLE[right]] = True

    return groupdict

def remove_acl(text):
  new_lines = []
  for line in text.split('\n'):
    if line.startswith('#acl '): continue
    new_lines.append(line)
  return '\n'.join(new_lines)

def get_group_members(groupname, request):
  members = {}
  page_text = Page(groupname, request).get_raw_body(fresh=True)
  for line in page_text.split('\n'):
    if line.startswith(' *'):
      username = line[len(' *'):].strip()
      members[username.lower()] = None
  return members
    
if wiki_name:
  req = request.RequestDummy(wiki_name=wiki_name)
else: 
  req = request.RequestDummy()

print "Removing/converting old ACL system to new system..."
plist = wikiutil.getPageList(req, objects=True)
for page in plist:
  print "  ", page.page_name
  page_text = page.get_raw_body(fresh=True)
  lines = page_text.split('\n')
  for line in lines:
    if line.startswith('#acl '):
      groupdict = parseACL(line[len('#acl '):])
      wikiacl.setACL(page.page_name, groupdict, req)
      new_page_text = remove_acl(page_text)
      req.cursor.execute("UPDATE curPages set text=%(page_text)s where name=%(page_name)s and wiki_id=%(wiki_id)s", {'page_text':new_page_text, 'page_name':page.page_name, 'wiki_id':req.config.wiki_id}, isWrite=True)
      req.cursor.execute("UPDATE allPages set text=%(page_text)s where name=%(page_name)s and wiki_id=%(wiki_id)s and editTime=%(mtime)s", {'page_text':new_page_text, 'page_name':page.page_name, 'wiki_id':req.config.wiki_id, 'mtime':page.mtime()}, isWrite=True)
      print "    ", "...converted!"
      break

print "Adding new user groups.."
for groupname in defined_user_groups:
  print "  ", groupname
  group = wikiacl.Group(groupname, req)
  groupdict = get_group_members(groupname, req)
  group.update(groupdict)
  group.save()

print "  ", admin_group, "->", 'Admin'
group = wikiacl.Group('Admin', req)
groupdict = get_group_members(admin_group, req)
group.update(groupdict)
group.save()

print "  ", banned_group, "->", 'Banned'
group = wikiacl.Group('Banned', req)
groupdict = get_group_members(banned_group, req)
group.update(groupdict)
group.save()

# note on group page that this is not how it's defined any more
for groupname in defined_user_groups + [admin_group, banned_group]:
    p = Page(groupname, req)
    if p.exists():
       new_body = p.get_raw_body() + '\n\n' + group_changed_message
       p.set_raw_body(new_body)
       req.cursor.execute("UPDATE curPages set text=%(new_body)s where name=%(pagename)s and wiki_id=%(wiki_id)s", {'new_body':new_body, 'pagename':p.page_name, 'wiki_id':req.config.wiki_id}, isWrite=True)
       req.cursor.execute("UPDATE allPages set text=%(new_body)s where name=%(pagename)s and editTime=%(mtime)s and wiki_id=%(wiki_id)s", {'new_body':new_body, 'pagename':p.page_name, 'mtime':p.mtime(), 'wiki_id':req.config.wiki_id}, isWrite=True)
       p.buildCache()

 
req.db_disconnect()
print "..Done!"
