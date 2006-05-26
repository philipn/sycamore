"""
   Developed by :
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
import os, time, threading
from Sycamore.support import Bogus
from Sycamore import config
from Sycamore.support import memcache

def fixKey(key):
  """
  Memcache needs the key encoded.  The python memcache module doesn't do this, so we have to.
  """
  new_key = key
  if type(key) == str:
    new_key = key.decode('utf-8')

  if type(new_key) == unicode:
    return new_key.encode('utf-8')

  return new_key

class MemcachePool:
    def __init__(self,hosts=None):
        self._pooled_conns=[]
        self.enabled = True
        if hosts:
            self._hosts=hosts
        else:
            self._hosts=self.getMCHosts()
        self.lock = threading.Lock()
        
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
        
    def get(self,key):
        mc = self.getConnection()
	key = fixKey(key)
        v = mc.get(key)
	if type(v) == str:
	  v = v.decode('utf-8')
        self.returnConnection(mc)
        return v

    def set(self,key,value,time=0):
        mc = self.getConnection()
	key = fixKey(key)
	value = fixKey(value)
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

    def add(self,key,value,time=0):
        mc = self.getConnection()
	key = fixKey(key)
	value = fixKey(value)
        r = mc.add(key,value,time)
        self.returnConnection(mc)
        return r

    def replace(self,key,value,time=0):
        mc = self.getConnection()
	key = fixKey(key)
        r = mc.replace(key,value,time)
        self.returnConnection(mc)
        return r

    def delete(self,key,time=0):
        mc = self.getConnection()
	key = fixKey(key)
        r = mc.delete(key,time)
        self.returnConnection(mc)
        return r

    def incr(self,name,value=1):
        mc = self.getConnection()
	name = fixKey(name)
        r = mc.incr(name,value)
        self.returnConnection(mc)
        return r

    def decr(self,name,value=1):
        mc = self.getConnection()
	name = fixKey(name)
        r = mc.decr(name,value)
        self.returnConnection(mc)
        return r

    def disconnect_all(self):
        self.lock.acquire()
        while len(self._pooled_conns):
            mc = self._pooled_conns.pop()
            mc.disconnect_all()
        self.lock.release()

    def get_multi(self,keys):
        mc = self.getConnection()
	keys = [ fixKey(key) for key in keys ]
        v = mc.get_multi(keys)
	v_new = []
	for value in v:
	  if type(value) == str:
	    v_new.append(value.decode("utf-8"))
	  else:
	    v_new.append(value)
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
