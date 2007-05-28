# -*- coding: iso-8859-1 -*-
"""
    Sycamore Dictionary / Group Functions

    @copyright: 2003 by Thomas Waldmann, http://linuxwiki.de/ThomasWaldmann
    @copyright: 2003 by Gustavo Niemeyer, http://moin.conectiva.com.br/GustavoNiemeyer
    @license: GNU GPL, see COPYING for details.
"""
import time, os
import cPickle as pickle
from Sycamore import config, wikiutil, Page

DICTS_PICKLE_VERSION = 1

# we use this in persistent environments, so we don't have to
# load the data with every new request:
DICTS_DATA = {}

class Dict:
    """a Dict - a mapping of keys to values

       How a Dict definition page should look like:

       any text does not care
        key1:: value1
        * does not care, too
        key2:: value2 containing spaces
        ...
        keyn:: ....
       any text does not care
       
       If dict=0, then groups are simulated by a dict:
       How a Group definition page should look like:

       any text does not care
        * member1
         * does not care, too
        * member2
        * ....
        * memberN
       any text does not care

       if there are any free links using ["free link"] notation, the markup
       is stripped from the member 
    """

    def __init__(self, name, request, dict=1, case_insensitive=True, fresh=False):
        """Initialize a Dict, starting from <nothing>.
        """
	import re
        self.name = name
        self._dict = {}
        p = Page.Page(name, request)
        if dict: # used for dicts
            regex = r'^\s(?P<key>.*?)::\s(?P<val>.*?)(\s*)$' # 1st level definition list,
                                               # strip trailing blanks
        else: # used for groups
            regex = r'^\s\*\s(\[\")?(?P<member>.*?)(\"\])?(\s*)$' # 1st level item list,
                               # strip trailing blanks and free link markup
        regex = re.compile(regex)
        text = p.get_raw_body(fresh=fresh)
        for line in text.split("\n"):
            match = regex.match(line)
            if match:
                mdict = match.groupdict()
                if dict:
                    key, value = mdict['key'].strip().lower(), mdict['val']
                else:
                    key, value = mdict['member'].lower(), 1
                self._dict[key] = value

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def has_key(self, key):
        return self._dict.has_key(key)

    def __getitem__(self, key):
        return self._dict[key]


class Group(Dict):
    """a Group - e.g. of users, of pages, of whatever

    """

    def __init__(self, name, request):
        """Initialize a Group, starting from <nothing>.
        """
        Dict.__init__(self, name, request, dict=0)

    def members(self):
        return self._dict.keys()

    def addmembers(self, members):
        for m in members:
            self.addmember(m)

    def addmember(self, member):
        self._dict[member.lower()] = 1

    def has_member(self, member):
        return self._dict.has_key(member.lower())

    def _expandgroup(self, groupdict, name):
        groupmembers = groupdict.members(name.lower())
        members = {}
        for member in groupmembers:
            if member == self.name:
                continue
            if groupdict.hasgroup(member):
                members.update(self._expandgroup(groupdict, member))
            else:
                members[member] = 1
        return members

    def expandgroups(self, groupdict):
        members = {}
        for member in self._dict.keys():
            if member == self.name:
                continue
            if groupdict.hasgroup(member):
                members.update(self._expandgroup(groupdict, member))
            else:
                members[member] = 1
        self._dict = members


class DictDict:
    """a dictionary of Dict objects

       Config:
           config.page_dict_regex
               Default: ".*Dict$"  Defs$ Vars$ ???????????????????
    """

    def __init__(self, request):
        self.reset()
	self.request = request
	self.cursor = request.cursor

    def reset(self):
        self.dictdict = {}
        self.namespace_timestamp = 0
        self.pageupdate_timestamp = 0
        self.picklever = DICTS_PICKLE_VERSION

    def has_key(self, dictname, key):
        dict = self.dictdict.get(dictname.lower())
        if dict and dict.has_key(key.lower()):
            return 1
        return 0

    def keys(self, dictname):
        """get keys of dict <dictname>"""
        try:
            dict = self.dictdict[dictname.lower()]
        except KeyError:
            return []
        return dict.keys()

    def values(self, dictname):
        """get values of dict <dictname>"""
        try:
            dict = self.dictdict[dictname.lower()]
        except KeyError:
            return []
        return dict.values()

    def dict(self, dictname):
        """get dict <dictname>"""
        try:
            dict = self.dictdict[dictname.lower()]
        except KeyError:
            return {}
        return dict

    def adddict(self, dictname):
        """add a new dict (will be read from the wiki page)"""
        self.dictdict[dictname.lower()] = Dict(dictname.lower(), self.request)

    def has_dict(self, dictname):
        return self.dictdict.has_key(dictname.lower())

    def keydict(self, key):
        """list all dicts that contain key"""
        dictlist = []
        key = key.lower()
        for dict in self.dictdict.values():
            if dict.has_key(key):
                dictlist.append(dict.name)
        return dictlist


class GroupDict(DictDict):
    """a dictionary of Group objects

       Config:
           config.page_group_regex
               Default: ".*Group$"
    """
    def __init__(self, request):
      self.request = request

    def has_member(self, groupname, member):
        groupname = groupname.lower()
        member = member.lower()
        group = self.dictdict.get(groupname)
        if group and group.has_member(member):
            return 1
        return 0

    def members(self, groupname):
        """get members of group <groupname>"""
        try:
            group = self.dictdict[groupname.lower()]
        except KeyError:
            return []
        return group.members()

    def addgroup(self, groupname):
        """add a new group (will be read from the wiki page)"""
        self.dictdict[groupname.lower()] = Group(groupname.lower(), self.request)

    def hasgroup(self, groupname):
        return self.dictdict.has_key(groupname.lower())

    def membergroups(self, member):
        """list all groups where member is a member of"""
        grouplist = []
        for group in self.dictdict.values():
            if group.has_member(member):
                grouplist.append(group.name)
        return grouplist

    def save(self):
       # save to disk and memcache the results of an add
       data = {
            "namespace_timestamp": self.namespace_timestamp,
            "pageupdate_timestamp": self.pageupdate_timestamp,
            "dictdict": self.dictdict,
            "picklever": self.picklever,
       } 
       picklefile = config.data_dir + '/dicts.pickle'
       pickle.dump(data, open(picklefile, 'w'), True)
       try:
         os.chmod(picklefile, 0666 & config.umask)
       except OSError:
         pass
       if config.memcache:
         self.request.mc.set('dicts_data', data)

    def scandicts(self, force_update=False, update_pagename=None):
        """scan all pages matching the dict / group regex and init the dictdict"""
        global DICTS_PICKLE_VERSION
        dump = 0
	if config.memcache:
	  DICTS_DATA = self.request.mc.get("dicts_data")
	else:
	  DICTS_DATA = {}

        if DICTS_DATA and not force_update:
            self.__dict__.update(DICTS_DATA)
        else:
	    DICTS_DATA = {}
            try:
                picklefile = config.data_dir + '/dicts.pickle'
                data = pickle.load(open(picklefile))
                self.__dict__.update(data)
                if self.picklever != DICTS_PICKLE_VERSION:
                    self.reset()
                    dump = 1
		if config.memcache:
		  self.request.mc.add('dicts_data', data)
            except:
                self.reset()

	# init the dicts the first time
	if not self.namespace_timestamp or force_update:
            now = time.time()
            if force_update and update_pagename:
               self.addgroup(update_pagename)
	    else:
              import re
              group_re = re.compile(config.page_group_regex, re.IGNORECASE)
              pagelist = wikiutil.getPageList(self.request)
              grouppages = filter(group_re.search, pagelist)
              #print '%s -> %s' % (config.page_group_regex, grouppages)
              for pagename in grouppages:
                  if not self.dictdict.has_key(pagename):
                      self.addgroup(pagename)
            self.namespace_timestamp = now
            dump = 1

        data = {
            "namespace_timestamp": self.namespace_timestamp,
            "pageupdate_timestamp": self.pageupdate_timestamp,
            "dictdict": self.dictdict,
            "picklever": self.picklever,
        }
        if dump:
            for pagename in self.dictdict:
                if update_pagename or group_re.search(pagename):
                    group = self.dictdict[pagename.lower()]
                    group.expandgroups(self)

	    if config.memcache: self.request.mc.set('dicts_data', data)
            pickle.dump(data, open(picklefile, 'w'), True)
            try:
                os.chmod(picklefile, 0666 & config.umask)
            except OSError:
                pass
