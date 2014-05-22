"""
   `Wrapper for memcached interface..does a little bit of other sycamore-specific stuff.

    Some specifics:

       * does prefixes for different 'namespaces'
       * errors on control characters rather than fucking memcached up
       * does hash-magic (TM) on long keys (>250 characters).

   originally Developed by :
      Jehiah Czebotar
      Aryeh Katz

   Released under Apache License 2.0
   Version 1.0 - January 24, 2006

   http://jehiah.com/download/MemcachePool.py.txt
   http://jehiah.com/download/Bogus.py.txt

   ---------------------

   edit the MemcachePool.getMCHosts() to suit your needs

   import MemcachePool
   mc = MemcachePool.getMC()
   mc.set(...)
   mc.get(...)

"""
import os, time, threading, inspect
from copy import copy
from Sycamore.support import Bogus
from Sycamore import config
# It would be cool to use cmemcache instead, when they have it, but:
#   * it's based on libmemcache and has bugs where if a connection drops it'll go into infinite stderr loops
#   * simply taking a server offline while Sycamore is running will crash Sycamore, at the fault of cmemcache's error handling (via libmemcache)
# It'd be cool to fix that stuff and make it work with cmemcache, but right now we'll just use the pure python implementation.
from Sycamore.support import memcache

from Sycamore.support.memcache import SERVER_MAX_KEY_LENGTH

class MemcachedKeyError(Exception):
    pass
class MemcachedKeyCharacterError(MemcachedKeyError):
    pass

def hash(cleartext):
    """
    hash of cleartext returned
    """
    import base64, hashlib, md5
    return '%s_%s' % (base64.encodestring(hashlib.new('sha1', cleartext.encode('utf-8')).digest()).rstrip()[:-1], base64.encodestring(md5.new(cleartext.encode('utf-8')).hexdigest())[:-2])


def check_key(key):
    """
    Checks to make sure the key doesn't contain control characters (this will FUCK UP memcached HARD).
    If test fails throws MemcachedKeyCharacter error.
    """
    for char in key:
      if ord(char) < 33:
        raise MemcachedKeyCharacterError, "Control characters not allowed"


def fixEncoding(item):
        """
        Memcache needs the items encoded.  The python memcache module doesn't do this, so we have to.
        """
        new_item = item
        if type(item) == str:
          new_item = item.decode('utf-8')
      
        if type(new_item) == unicode:
          return new_item.encode('utf-8')
      
        return new_item

def fixKey(key, prefix):
        """
        Fix the encoding and also add self.prefix to the key.
        """        
        if prefix != '':
          return fixEncoding('%s%s' % (prefix, key))
        key = fixEncoding(key)
        check_key(key) # check for control characters
        return key


class MemcachePool:
    def __init__(self,hosts=None,prefix=''):
        self._pooled_conns=[]
        self.enabled = True
        if prefix != '':
            self.prefix = prefix
        else:
            self.prefix = ''
        if hosts:
            self._hosts=hosts
        else:
            self._hosts=self.getMCHosts()
        self.lock = threading.Lock()

    def setPrefix(self, prefix):
        self.prefix = prefix

    def enable(self):
        self.enabled = True
    def disable(self):
        self.enabled = False

    def getMCHosts(self):
        return config.memcache_servers

    def addConnection(self):
        try:
            mc = memcache.Client(self._hosts)
        except:
            print "creating bogus exception"
            mc = Bogus.Bogus()
        return mc

    def getConnection(self):
        if not self.enabled:
            return Bogus.Bogus()

        self.lock.acquire()
        if len(self._pooled_conns) > 0:
            mc = self._pooled_conns.pop()
        else:
            mc = self.addConnection()
        self.lock.release()    
        return mc

    def returnConnection(self,mc):
        # never return bogus memcache client to the pool
        if  not isinstance(mc,Bogus.Bogus):
            self.lock.acquire()
            self._pooled_conns.append(mc)
            self.lock.release()
        
    def get(self,key,wiki_global=False,prefix=None):
        if prefix is None: prefix = self.prefix
        mc = self.getConnection()
        if not wiki_global:
          key = fixKey(key, prefix)
        else:
          key = fixKey(key, '')
        if len(key) > SERVER_MAX_KEY_LENGTH:
            v = mc.get(hash(key))
            if v is not None:
                value, orig_key = v
                if key == orig_key:
                    v = value
                else:
                    # crazy collision omg
                    v = None
        else:
            v = mc.get(key)
        if type(v) == str:
          v = v.decode('utf-8')
        self.returnConnection(mc)
        return v

    def set(self,key,value,time=0,wiki_global=False,prefix=None):
        if prefix is None: prefix = self.prefix
        mc = self.getConnection()
        if not wiki_global:
          key = fixKey(key, prefix)
        else:
          key = fixKey(key, '')
        if len(key) > SERVER_MAX_KEY_LENGTH:
            value = (fixEncoding(value), key)
            key = hash(key)
        else:
            value = fixEncoding(value)

        r = mc.set(key,value,time)
        self.returnConnection(mc)
        return r

    def flush_all(self):
        mc = self.getConnection()
        r = mc.flush_all()
        # fix for memcache delete,set bug
        time.sleep(1)
        self.returnConnection(mc)
        return r

    def add(self,key,value,time=0,wiki_global=False,prefix=None):
        if prefix is None: prefix = self.prefix
        mc = self.getConnection()
        if not wiki_global:
          key = fixKey(key, prefix)
        else:
          key = fixKey(key, '')
        if len(key) > SERVER_MAX_KEY_LENGTH:
            value = (fixEncoding(value), key)
            key = hash(key)
        else:
            value = fixEncoding(value)
        r = mc.add(key,value,time)
        self.returnConnection(mc)
        return r

    def replace(self,key,value,time=0,wiki_global=False,prefix=None):
        if prefix is None: prefix = self.prefix
        mc = self.getConnection()
        if not wiki_global:
          key = fixKey(key, prefix)
        else:
          key = fixKey(key, '')
        if len(key) > SERVER_MAX_KEY_LENGTH:
            value = (fixEncoding(value), key)
            key = hash(key)
        else:
            value = fixEncoding(value)
        r = mc.replace(key,value,time)
        self.returnConnection(mc)
        return r

    def delete(self,key,time=0,wiki_global=False,prefix=None):
        if prefix is None: prefix = self.prefix
        mc = self.getConnection()
        if not wiki_global:
          key = fixKey(key, self.prefix)
        else:
          key = fixKey(key, '')
        if len(key) > SERVER_MAX_KEY_LENGTH:
            key = hash(key)
        r = mc.delete(key,time)
        self.returnConnection(mc)
        return r

    def incr(self,name,value=1, wiki_global=False,prefix=None):
        if prefix is None: prefix = self.prefix
        mc = self.getConnection()
        if not wiki_global:
          name = fixKey(name, prefix)
        else:
          name = fixKey(name, '')
        if len(name) > SERVER_MAX_KEY_LENGTH:
            value = (fixEncoding(value), name)
            name = hash(name)
        else:
            value = fixEncoding(value)
        r = mc.incr(name,value)
        self.returnConnection(mc)
        return r

    def decr(self,name,value=1, wiki_global=False,prefix=None):
        if prefix is None: prefix = self.prefix
        mc = self.getConnection()
        if not wiki_global:
          name = fixKey(name, prefix)
        else:
          name = fixKey(name, '')
        if len(name) > SERVER_MAX_KEY_LENGTH:
            value = (fixEncoding(value), name)
            name = hash(name)
        else:
            value = fixEncoding(value)
        r = mc.decr(name,value)
        self.returnConnection(mc)
        return r

    def disconnect_all(self):
        self.lock.acquire()
        while len(self._pooled_conns):
            mc = self._pooled_conns.pop()
            mc.disconnect_all()
        self.lock.release()

    def get_multi(self,keys,wiki_global=False,prefix=None):
        if not prefix: prefix = self.prefix
        mc = self.getConnection()
        orig_keys = []
        get_keys = []
        for key in keys:
          if not wiki_global:
              key = fixKey(key, self.prefix)
          else:
              key = fixKey(key, '')
          if len(key) > SERVER_MAX_KEY_LENGTH:
              orig_keys.append(key)
              key = hash(key)
          else:
              orig_keys.append(None) # just padding
          get_keys.append(key)

        v = mc.get_multi(get_keys)
        v_new = {}
        i = 0
        for key in v:
          got_value = v[key]
          value = got_value
          if orig_keys[i]: # we hashed
            value, orig_key = got_value
            if orig_key != orig_keys[i]: # collision of some sort
                value = None

          if type(value) == str:
            value = value.decode("utf-8")
          v_new[key] = value
          i += 1

        v = v_new
        self.returnConnection(mc)
        return v

    def get_stats(self):
        mc = self.getConnection()
        r = mc.get_stats()
        self.returnConnection(mc)
        return r

_globalMemcachePool = MemcachePool()

def getMC():
    return _globalMemcachePool
