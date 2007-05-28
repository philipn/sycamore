# -*- coding: iso-8859-1 -*-
"""
    Sycamore Access Control Lists

    @copyright: 2006 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2003 by Thomas Waldmann, http://linuxwiki.de/ThomasWaldmann
    @copyright: 2003 by Gustavo Niemeyer, http://moin.conectiva.com.br/GustavoNiemeyer
    @license: GNU GPL, see COPYING for details.
"""

from Sycamore import config, user
from Sycamore.wikiutil import mc_quote
from copy import copy

ACL_RIGHTS_TABLE = {}
for i, entry in enumerate(config.acl_rights_valid):
  ACL_RIGHTS_TABLE[entry] = i

special_groups = ["All", "Known", "Admin", "Banned"]

class AccessControlList:
    """
    Access Control List

    Control who may do what on or with a wiki page.
    """


    def __init__(self, request, dict={}):
        """Initialize an ACL.
        """
        self.acl_dict_defaults = request.config.acl_rights_default
        self.acl_dict = dict

    def grouplist(self):
        """
        Returns a list of the definied user groups.
        """
        return self.acl_dict_defaults.keys()

    def may(self, request, username, dowhat):
        """May <username> <dowhat>?
           Returns boolean answer.
        """
        if username in Group('Admin', request):
            return True  # Admin group owns all
        allowed = None
        has_all_setting = ('All' in self.acl_dict)
        has_known_setting = ('Known' in self.acl_dict)

        # page-specific acl
        in_page_group = False
        for groupname in self.acl_dict:
          if groupname in ['All', 'Known', 'Banned', 'Admin']: continue
          allowed = self.acl_dict[groupname][ACL_RIGHTS_TABLE[dowhat]]
          if username in Group(groupname, request):
              if allowed:
                  return True
              in_page_group = True

        # fall-back:
        # user is in a group with defined security settings on this page
        # but isn't granted any rights, so we exclude them.
        if in_page_group:
            return False

        # if they're banned, kick 'em out
        banned_group = Group("Banned", request)
        if (username in banned_group) or (request.remote_addr in banned_group.get_ips()):
            allowed = self.acl_dict_defaults["Banned"][ACL_RIGHTS_TABLE[dowhat]]
            return allowed

        if request.user.valid:
          # we fall back to Known behavior if there is something specific to Known on this page
          if self.acl_dict.has_key('Known'):
             allowed = self.acl_dict["Known"][ACL_RIGHTS_TABLE[dowhat]]
             return allowed
        else:
          # we fall back to ALl behavior if there is something specific to All on this page
          if self.acl_dict.has_key('All'):
             allowed = self.acl_dict["All"][ACL_RIGHTS_TABLE[dowhat]]
             return allowed


        # no specific settings for Known on this page, so let's do what the default for the group is
        defaults_without_special = copy(request.config.acl_rights_default.keys())
        defaults_without_special.remove("All") 
        defaults_without_special.remove("Known") 
        defaults_without_special.remove("Admin") 
        defaults_without_special.remove("Banned") 
        for groupname in defaults_without_special:
          allowed = request.config.acl_rights_default[groupname][ACL_RIGHTS_TABLE[dowhat]]
          if username in Group(groupname, request) and allowed:
            return True

        for groupname in ["Known", "All"]:
          if groupname == 'Known' and has_known_setting: break
          if groupname == 'All' and has_all_setting: break
          allowed = request.config.acl_rights_default[groupname][ACL_RIGHTS_TABLE[dowhat]]
          if username in Group(groupname, request) and allowed:
            return True

        return False


class Group(object):
  def __init__(self, name, request, fresh=False):
    self.name = name
    self.request = request
    self.add_users = []
    self.remove_users = []
    self.add_ips = []
    self.remove_ips = []
    self.groupdict = None
    self.ips = None
    self.fresh = fresh
    
    if self.request.config.acl_rights_default.has_key(self.name):
      self.acl_rights_default = self.request.config.acl_rights_default[self.name]
    else: 
      self.acl_rights_default = self.request.config.acl_rights_default['Known']

  def _init_groupdict(self):
    if self.groupdict is None:
        if (self.name == 'All') or (self.name == 'Known'):
           self.groupdict = {}
           return

        groupdict = None
        if not self.fresh:
          if self.request.req_cache['group_dict'].has_key((self.name, self.request.config.wiki_id)):
            self.groupdict = self.request.req_cache['group_dict'][(self.name, self.request.config.wiki_id)]
            return

          if config.memcache:
            groupdict = self.request.mc.get('groupdict:%s' % mc_quote(self.name))

        if groupdict is None:
          groupdict = {}
          d = {'groupname':self.name, 'wiki_id': self.request.config.wiki_id}
          self.request.cursor.execute("SELECT username from userGroups where groupname=%(groupname)s and wiki_id=%(wiki_id)s", d)
          results = self.request.cursor.fetchall()
          if results:
            for item in results:
              groupdict[item[0]] = None
          if config.memcache and not self.fresh:
             self.request.mc.add('groupdict:%s' % mc_quote(self.name), groupdict)

        self.request.req_cache['group_dict'][(self.name, self.request.config.wiki_id)] = groupdict
        self.groupdict = groupdict

  def _init_ips(self):
    if self.ips is None:
        if (self.name == 'All') or (self.name == 'Known'):
           self.ips = {}
           return

        ips = None
        if not self.fresh:
          if self.request.req_cache['group_ips'].has_key((self.name, self.request.config.wiki_id)):
            self.ips = self.request.req_cache['group_ips'][(self.name, self.request.config.wiki_id)]
            return

          if config.memcache:
            ips = self.request.mc.get('groupips:%s' % mc_quote(self.name))

        if ips is None:
          ips = {}
          d = {'groupname':self.name, 'wiki_id': self.request.config.wiki_id}
          self.request.cursor.execute("SELECT ip from userGroupsIPs where groupname=%(groupname)s and wiki_id=%(wiki_id)s", d)
          results = self.request.cursor.fetchall()
          if results:
            for item in results:
              ips[item[0]] = None
          if config.memcache and not self.fresh:
             self.request.mc.add('groupips:%s' % mc_quote(self.name), ips)

        self.request.req_cache['group_ips'][(self.name, self.request.config.wiki_id)] = ips 
        self.ips = ips


  def default_rights(self):
    """
    Return (may read, may edit, may delete, may admin) tuple of default rights for the group.
    """
    return self.acl_rights_default

  def set_default_rights(self, default_rights, request):
    self.acl_rights_default = default_rights
    request.config.acl_rights_default[self.name] = self.acl_rights_default
    # sets the config -- becomes active as soon as this line is executed!
    request.config.set_config(request.config.wiki_name, request.config.get_dict(), self.request)

  def add(self, username):
    self._init_groupdict()
    if not username in self.groupdict:
      self.add_users.append(username)
      self.groupdict[username] = None

  def remove(self, username):
    self._init_groupdict()
    if username in self.groupdict:
      del self.groupdict[username]
      self.remove_users.append(username)

  def add_ip(self, ip):
    self._init_ips()
    if not ip in self.ips:
      self.add_ips.append(ip)
      self.ips[ip] = None

  def remove_ip(self, ip):
    self._init_ips()
    if ip in self.ips:
      del self.ips[ip]
      self.remove_ips.append(ip)


  def update(self, dict):
    """
    Given a dictionary of the form {username: None ..}, this will update the group list.  The group will then contain only the members specified in the dictionary provided.
    """
    self._init_groupdict()

    add_users = []
    remove_users = []

    for username in dict:
      if username in self.groupdict:
        continue   
      else:
        add_users.append(username) 

    for username in self.groupdict:
      if username not in dict:
        remove_users.append(username)

    for username in add_users:
      self.add(username)
    for username in remove_users:
      self.remove(username)

  def update_ips(self, dict):
    """
    Given a dictionary of the form {ip_addr: None ..}, this will update the ip list.  The group will then contain only the ips specified in the dictionary provided as its IP address (normal 'users' will still be there).
    """
    self._init_ips()
    add_ips = []
    remove_ips = []

    for ip in dict:
      if ip in self.ips:
        continue   
      else:
        add_ips.append(ip) 

    for ip in self.ips:
      if ip not in dict:
        remove_ips.append(ip)

    for ip in add_ips:
      self.add_ip(ip)
    for ip in remove_ips:
      self.remove_ip(ip)


  def save(self):
    d = {'groupname':self.name, 'wiki_id': self.request.config.wiki_id}
    if self.groupdict is not None:
        for username in self.add_users:
          d['username'] = username
          self.request.cursor.execute("INSERT into userGroups (username, groupname, wiki_id) values (%(username)s, %(groupname)s, %(wiki_id)s)", d, isWrite=True)
        for username in self.remove_users:
          d['username'] = username
          self.request.cursor.execute("DELETE from userGroups where username=%(username)s and groupname=%(groupname)s and wiki_id=%(wiki_id)s", d, isWrite=True)

        if config.memcache:
          self.request.mc.set('groupdict:%s' % mc_quote(self.name), self.groupdict)

        self.request.req_cache['group_dict'][(self.name, self.request.config.wiki_id)] = self.groupdict

    if self.ips is not None:
        for ip in self.add_ips:
          d['ip'] = ip
          self.request.cursor.execute("INSERT into userGroupsIPs (ip, groupname, wiki_id) values (%(ip)s, %(groupname)s, %(wiki_id)s)", d, isWrite=True)
        for ip in self.remove_ips:
          d['ip'] = ip
          self.request.cursor.execute("DELETE from userGroupsIPs where ip=%(ip)s and groupname=%(groupname)s and wiki_id=%(wiki_id)s", d, isWrite=True)

        if config.memcache:
          self.request.mc.set('groupips:%s' % mc_quote(self.name), self.ips)

        self.request.req_cache['group_ips'][(self.name, self.request.config.wiki_id)] = self.ips


    if self.name not in self.request.config.acl_rights_default:
      self.request.config.acl_rights_default[self.name] = self.request.config.acl_rights_default["Known"]
      # sets the config -- becomes active as soon as this line is executed!
      self.request.config.set_config(self.request.config.wiki_name, self.request.config.get_dict(), self.request)


  def __contains__(self, username):
    self._init_groupdict()
    if self.name == 'All':
      return True
    elif self.name == 'Known':
      return user.User(self.request, id=user.getUserId(username, self.request)).valid
 
    if self.groupdict.has_key(username): return True 

    return False

  def users(self, proper_names=False):
    """
    Returns a list of the user names belonging to the group.
    """
    self._init_groupdict()
    if not proper_names:
       return self.groupdict.keys()
    
    proper_names = []
    for username in self.groupdict.keys():
      user_id = user.getUserId(username, self.request)
      if user_id: proper_names.append(user.User(self.request, id=user_id).propercased_name)
      else: proper_names.append(username)
    return proper_names

  def may(self, page, dowhat):
    page_acl_dict = getACL(page.page_name, self.request).acl_dict
    if page_acl_dict.has_key(self.name):
      return page_acl_dict[self.name][ACL_RIGHTS_TABLE[dowhat]]
    # fall back to known
    if page_acl_dict.has_key('Known'):
      return page_acl_dict['Known'][ACL_RIGHTS_TABLE[dowhat]]
    return self.acl_rights_default[ACL_RIGHTS_TABLE[dowhat]]

  def get_ips(self):
    """
    Returns a dict of the IP addresses belonging to the group.
    This is basically used for the Banned users.
    """
    self._init_ips()
    if self.ips:
      return self.ips
    return {}
    

def getACL(pagename, request):
   acl_dict = None
   got_from_mc = False
   pagename = pagename.lower()
   if request.req_cache['acls'].has_key((pagename, request.config.wiki_id)):
     return request.req_cache['acls'][(pagename, request.config.wiki_id)]
   if config.memcache:
     acl_dict = request.mc.get('acl:%s' % mc_quote(pagename))

   if acl_dict is None:
     acl_dict = {}
     d = {'pagename': pagename, 'wiki_id': request.config.wiki_id}
     request.cursor.execute("SELECT groupname, may_read, may_edit, may_delete, may_admin from pageAcls where pagename=%(pagename)s and wiki_id=%(wiki_id)s", d) 
     results = request.cursor.fetchall()
     if results:
       for groupname, may_read, may_edit, may_delete, may_admin in results:
         acl_dict[groupname] = (may_read, may_edit, may_delete, may_admin) 
   else:
     got_from_mc = True

   if acl_dict:
     acl = AccessControlList(request, dict=acl_dict)
   else:
     acl = AccessControlList(request)

   if config.memcache and not got_from_mc:
     request.mc.add('acl:%s' % mc_quote(pagename), acl_dict)
   request.req_cache['acls'][(pagename, request.config.wiki_id)] = acl

   return acl

def _sameAsDefaults(groupdict, request):
   """
   Is groupdict, consisting of permissions for groups, essentially the same as the default ACL rights on the wiki?
   """
   defaults = {}
   for groupname in request.config.acl_rights_default:
     # we don't let the banned or admin groups be altered on a page because it's pointless
     if groupname != 'Banned' and groupname != 'Admin':
       defaults[groupname] = list(request.config.acl_rights_default[groupname])

   return (defaults == groupdict)
   

def setACL(pagename, groupdict, request):
   from Sycamore.Page import Page
   pagename = pagename.lower()
   d = {'pagename': pagename, 'wiki_id': request.config.wiki_id}
   page = Page(pagename, request)
   
   for groupname in groupdict:
     group = Group(groupname, request, fresh=True)
     ## don't change if the settings are same as the current settings
     #if (group.may(page,'read') == groupdict[groupname][ACL_RIGHTS_TABLE['read']]) and \
     #   (group.may(page,'edit') == groupdict[groupname][ACL_RIGHTS_TABLE['edit']]) and \
     #   (group.may(page,'delete') == groupdict[groupname][ACL_RIGHTS_TABLE['delete']]) and \
     #   (group.may(page,'admin') == groupdict[groupname][ACL_RIGHTS_TABLE['admin']]):
     #   continue

     d['groupname'] = groupname
     d['may_read'] = groupdict[groupname][ACL_RIGHTS_TABLE['read']]
     d['may_edit'] = groupdict[groupname][ACL_RIGHTS_TABLE['edit']]
     d['may_delete'] = groupdict[groupname][ACL_RIGHTS_TABLE['delete']]
     d['may_admin'] = groupdict[groupname][ACL_RIGHTS_TABLE['admin']]
     request.cursor.execute("SELECT groupname from pageAcls where pagename=%(pagename)s and wiki_id=%(wiki_id)s and groupname=%(groupname)s", d)
     if request.cursor.fetchone():
       request.cursor.execute("UPDATE pageAcls set may_read=%(may_read)s, may_edit=%(may_edit)s, may_delete=%(may_delete)s, may_admin=%(may_admin)s where groupname=%(groupname)s and pagename=%(pagename)s and wiki_id=%(wiki_id)s", d, isWrite=True)
     else:
       request.cursor.execute("INSERT into pageAcls (groupname, pagename, may_read, may_edit, may_delete, may_admin, wiki_id) values (%(groupname)s, %(pagename)s, %(may_read)s, %(may_edit)s, %(may_delete)s, %(may_admin)s, %(wiki_id)s)", d, isWrite=True)

   # if the settings are the same then we clear them out so master changes can propagate through
   if _sameAsDefaults(groupdict, request):
      request.cursor.execute("DELETE from pageAcls where pagename=%(pagename)s and wiki_id=%(wiki_id)s", d, isWrite=True) 

   if config.memcache:
     if _sameAsDefaults(groupdict, request): # want to clear out when it's the same as the global defaults.  this way changes to global settings will affect the page if it's not special in any way, priv-wise.
       request.mc.set('acl:%s' % mc_quote(pagename), {})
     else:
       request.mc.set('acl:%s' % mc_quote(pagename), groupdict)

   # set for this request
   if groupdict:
     request.req_cache['acls'][(pagename, request.config.wiki_id)] = AccessControlList(request, dict=groupdict)
   else:
     request.req_cache['acls'][(pagename, request.config.wiki_id)] = AccessControlList(request)
