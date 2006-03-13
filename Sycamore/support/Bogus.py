"""
  Dummy (bogus) Memcache Client

  see MemcachePool.py for license info

"""

class Bogus:
    def __init__(self, selfShuntObj=None):
        pass
    
    def set(self, name, value,time=0):
        return 0
    
    def add(self, name, value,time=0):
        return 0
    
    def replace(self, name, value,time=0):
        return 0
    
    def delete(self, name,time=0):
        return 0
    
    def incr(self, name,value=1):
        return 0
    
    def decr(self, name,value=1):
        return 0
    
    def get(self, name):
        return None
    
    def flush_all(self):
        pass
    
    def debuglog(self, str):
        pass
    
    def disconnect_all(self):
        pass
    
    def forget_dead_hosts(self):
        pass
    
    def get_multi(self, keys):
        return None
    
    def get_stats(self):
        return None
    
    def set_servers(self, keys):
        pass
