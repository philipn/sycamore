#!/usr/bin/python -OO
# -*- coding: utf-8 -*-

# Imports
import sys
import socket
import getopt
import threading
import time
import copy
import os
import cPickle
import random

import __init__
__directory__ = os.path.dirname(__file__)
share_directory = os.path.abspath(os.path.join(__directory__, '..', 'share'))
sys.path.extend([share_directory]),

from Sycamore import request
from Sycamore import wikiutil
from Sycamore import search
from Sycamore import config
from Sycamore.Page import Page

if config.has_xapian:
    import xapian

# the amount of time to wait, in seconds, until processing a spool
SPOOL_WAIT_TIME = 10 
# amount of time in seconds to wait until commiting a batch of xapian changes
COMMIT_TIME_THRESHOLD = 60 

keep_processing = True

transaction_start_time = None
in_transaction = False

doing_db_rebuild = False
tmp_db_location = None
db_location = None
in_re_init = False
db_files_moving = False

DEBUG = True
MAX_RETRY_OPEN = 10 

def debug_log(t):
    if DEBUG:
        sys.stdout.write(t + '\n')
        sys.stdout.flush()

def _search_sleep_time(delta=0):
    """
    Sleep for a bit before trying to hit the db again. 
    """
    sleeptime = 0.1 + random.uniform(0, .05) + delta
    time.sleep(sleeptime)    


class Spool(object):
    def __init__(self):
        self.item_dict = {}
        self.item_queue = []

    def _mark(self, item, label):
      if not item in self.item_dict or not self.item_dict[item] != label:
          self.item_queue.append(item)
          self.item_dict[item] = label

    def mark_for_add(self, item):
        self._mark(item, 'add')

    def mark_for_remove(self, item):
        self._mark(item, 'del')

    def clear(self):
        self.item_dict = {}
        self.item_queue = []


def setup_databases(given_db_location=None):
    global db_location
    tried_times = 0
    while 1:
        try:
            debug_log("Attempting to open title db.")
            title_database = xapian.WritableDatabase(
              os.path.join(given_db_location or db_location, 'title'),
              xapian.DB_CREATE_OR_OPEN)
        except IOError, err:
            strerr = str(err) 
            debug_log("Had error opening title db.")
            if strerr == ('DatabaseLockError: Unable to acquire database '
                          'write lock %s' % os.path.join(
                            os.path.join(given_db_location or db_location,
                            'title'), 'db_lock')):
                cleanup_file_locks()
                _search_sleep_time()
            else:
                raise IOError, err
        except Exception, err:
            if tried_times <= MAX_RETRY_OPEN:
                # remove lock, if it's there, and try again 
                tried_times += 1
                cleanup_file_locks()
                _search_sleep_time()
            else:
                raise Exception, err
        else:
            break
    
    tried_times = 0
    while 1:
        try:
            debug_log("Attempting to open text db.")
            text_database = xapian.WritableDatabase(
              os.path.join(given_db_location or db_location, 'text'),
              xapian.DB_CREATE_OR_OPEN)
        except IOError, err:
            debug_log("Had error opening text db.")
            strerr = str(err) 
            if strerr == ('DatabaseLockError: Unable to acquire database '
                          'write lock %s' % os.path.join(
                            os.path.join(given_db_location or db_location,
                            'title'), 'db_lock')):
                cleanup_file_locks()
                _search_sleep_time()
            else:
                raise IOError, err
        except Exception, err:
            if tried_times <= MAX_RETRY_OPEN:
                # remove lock, if it's there, and try again 
                tried_times += 1
                cleanup_file_locks()
                _search_sleep_time()
            else:
                raise Exception, err
        else:
            break

    debug_log("Opened DBs successfully")
    return (text_database, title_database)

spool_lock = threading.Lock()
spool = Spool()

text_database_lock = threading.Lock()
title_database_lock = threading.Lock()

def usage():
        print "usage: syc_search_server -l <location of databases> [-h <host>",
        print "-p <port> -d]"
        print ""
        print " h : what IP/domain to bind to."
        print " p : what port to use (defaults to 33432)."
        print " l : location of the search directory containing title and",
        print "text databases."
        print " d : run as daemon."
        print ""

def cleanup_file_locks():
        if os.path.exists(os.path.join(os.path.join(config.search_db_location,
                                                    "text"), 'db_lock')):
            os.remove(os.path.join(os.path.join(config.search_db_location,
                                                "text"), 'db_lock'))
        if os.path.exists(os.path.join(os.path.join(config.search_db_location,
                                                    "title"), 'db_lock')):
            os.remove(os.path.join(os.path.join(config.search_db_location,
                                                "title"), 'db_lock'))

def process_search(terms, wiki_name, client, p_start_loc, t_start_loc):
    global db_location, db_files_moving
    req = request.RequestDummy()
    if wiki_name:
        req.switch_wiki(wiki_name)
        wiki_global = False
    else:
        wiki_global = True

    i = 0
    while db_files_moving:
        i += 1
        time.sleep(1) 
	if i > 30:
       	    output = client.makefile('w',0)
       	    output.write("\n\nE\n\n")
            req.db_disconnect()
	    return

    thesearch = search.XapianSearch(None, req, db_location=db_location,
                                    processed_terms=terms,
                                    wiki_global=wiki_global,
                                    p_start_loc=p_start_loc,
                                    t_start_loc=t_start_loc)
    thesearch.process()
    results = (thesearch.title_results, thesearch.text_results)
    thesearch_encoded = wikiutil.quoteFilename(cPickle.dumps(results))
    output = client.makefile('w',0)
    output.write(thesearch_encoded)
    output.write("\n\nE\n\n")
    req.db_disconnect()
    del req

def _begin_xapian_transaction():
    global text_database, title_database, transaction_start_time
    global in_transaction
    debug_log("Beginning Xapian transaction")
    text_database.begin_transaction()
    title_database.begin_transaction()
    transaction_start_time = time.time()
    in_transaction = True

def force_commit_xapian_transaction():
    global text_database, title_database, transaction_start_time
    global in_transaction, text_database_lock, title_database_lock
    debug_log("Forcing commit of Xapian transaction..")
    if in_transaction:
        debug_log("..in transaction, asking for locks..")
        text_database_lock.acquire()
        title_database_lock.acquire()
        debug_log("got locks!")
        text_database.commit_transaction()
        title_database.commit_transaction()
        debug_log("commited transaction")
        text_database_lock.release()
        title_database_lock.release()
        debug_log("released locks")
    in_transaction = False

def cleanup_db_init():
    global tmp_db_location, text_database, title_database
    global text_database_lock, title_database_lock, in_re_init, db_files_moving
    debug_log("in db init cleanup")
    # do switchover of title_db and text_db to the normal location
    debug_log("attempting to acquire locks in db_init cleanup..")
    text_database_lock.acquire()
    title_database_lock.acquire()
    debug_log("locks acquired in db_init cleanup")
    in_re_init = False
    debug_log("doing a force_commit in db_init cleanup..")
    force_commit_xapian_transaction()
    debug_log("force commit successful in db_init cleanup")
    # in posix os.rename is atomic
    db_files_moving = True
    for filename in os.listdir(os.path.join(tmp_db_location, "title")):
        os.rename(os.path.join(os.path.join(tmp_db_location, "title"),
                               filename),
                  os.path.join(os.path.join(config.search_db_location,
                                            "title"),
                               filename))

    for filename in os.listdir(os.path.join(tmp_db_location, "text")):
        os.rename(os.path.join(os.path.join(tmp_db_location, "text"),
                               filename),
                  os.path.join(os.path.join(config.search_db_location, "text"),
                               filename))

    os.rmdir(os.path.join(tmp_db_location, "title"))
    os.rmdir(os.path.join(tmp_db_location, "text"))
    os.rmdir(os.path.join(tmp_db_location))

    cleanup_file_locks()
    
    del text_database
    del title_database
    db_files_moving = False
    debug_log("attempting to set up databases in db_init cleanup")
    time.sleep(30)
    text_database, title_database = setup_databases()

    debug_log("releasing locks in db_init cleanup")
    text_database_lock.release()
    title_database_lock.release()

def process_spool(spool):
    global db_location, title_database, text_database
    global transaction_start_time, in_transaction, in_re_init, doing_db_rebuild
    if not spool.item_queue:
        return

    debug_log("in process_spool")
    req = request.RequestDummy()
    debug_log("attempting to begin xap transaction in process spool")
    _begin_xapian_transaction()
    debug_log("in transaction in process spool")
    while spool.item_queue:
        item = spool.item_queue.pop(0)
        type = spool.item_dict[item]
        pagename, wiki_name = item
        if wiki_name:
            page = Page(pagename, req, wiki_name=wiki_name)
        else:
            page = Page(pagename, req)

        if type == 'add':
            debug_log("attempting to acquire lock in process spool")
            text_database_lock.acquire()
            title_database_lock.acquire()
            debug_log("lock acquired in process spool")
            if doing_db_rebuild:
                in_re_init = True
            try:
                search.index(page, text_db=text_database,
                             title_db=title_database)
            except RuntimeError, msg:
                debug_log("had error in process spool (first search index)")
                msg = str(msg)
                if (msg == 'unknown error in Xapian' or
                    msg == ("UnimplementedError: Can't open modified postlist "
                            "during a transaction")):
                        debug_log("releasing lock in process spool")
                        text_database_lock.release()
                        title_database_lock.release()
                        debug_log("forcing commit in process spool")
                        force_commit_xapian_transaction()
                        time.sleep(1)
                        _search_sleep_time()
                        debug_log("attempting to reopen db's in process spool")
                        text_database.reopen()
                        title_database.reopen()
                        debug_log("attempting to force commit in process spool")
                        force_commit_xapian_transaction()
                        debug_log("forced commit in process spool")
                        debug_log("attempting to acquire locks in "
                                  "process spool")
                        text_database_lock.acquire()
                        title_database_lock.acquire()
                        debug_log("locks acquired in process spool")
                        try:
                            search.index(page, text_db=text_database,
                                         title_db=title_database)
                        except RuntimeError, msg:
                            debug_log("had error on search index in "
                                      "process spool")
                            msg = str(msg)
                            if msg == 'unknown error in Xapian':
                                    spool.item_queue.append(item)
                                    debug_log("releasing locks in "
                                              "process spool")
                                    text_database_lock.release()
                                    title_database_lock.release()
                                    return
                            else:
                                    debug_log("releasing locks in "
                                              "process spool")
                                    text_database_lock.release()
                                    title_database_lock.release()
                                    raise
                        
                else:
                    debug_log("releasing locks in process spool")
                    text_database_lock.release()
                    title_database_lock.release()
                    raise

            debug_log("releasing locks in process spool")
            text_database_lock.release()
            title_database_lock.release()

        elif type == 'del':
            debug_log("attempting to acquire lock in process spool")
            text_database_lock.acquire()
            title_database_lock.acquire()
            if doing_db_rebuild:
               in_re_init = True
            try:
                search.remove(page, text_db=text_database,
                              title_db=title_database)
            except RuntimeError, msg:
                debug_log("had error in process spool (first remove)")
                msg = str(msg)
                if (msg == 'unknown error in Xapian' or
                    msg == ("UnimplementedError: Can't open modified "
                            "postlist during a transaction")):
                        debug_log("releasing locks in process spool")
                        text_database_lock.release()
                        title_database_lock.release()
                        debug_log("attempting to force commit of "
                                  "xap transaction in process spool")
                        force_commit_xapian_transaction()
                        debug_log("forced commit of xap transaction "
                                  "in process spool")
                        time.sleep(1)
                        _search_sleep_time()
                        debug_log("re-opening xapian db's")
                        text_database.reopen()
                        title_database.reopen()
                        debug_log("xapian db's reopened")
                        debug_log("attempting to force commit of xap "
                                  "transaction in process spool (2)")
                        force_commit_xapian_transaction()
                        debug_log("forced commit of xap transaction in "
                                  "process spool (2)")
                        debug_log("attempting to acquire locks in "
                                  "process spool (2)")
                        text_database_lock.acquire()
                        title_database_lock.acquire()
                        try:
                            search.remove(page, text_db=text_database,
                                          title_db=title_database)
                        except RuntimeError, msg:
                            debug_log("had ANOTHER error in "
                                      "process spool (remove)")
                            msg = str(msg)
                            if msg == 'unknown error in Xapian':
                                    spool.item_queue.append(item)
                                    debug_log("releasing locks "
                                              "in process spool")
                                    text_database_lock.release()
                                    title_database_lock.release()
                                    return
                            else:
                                    debug_log("releasing locks in "
                                              "process spool")
                                    text_database_lock.release()
                                    title_database_lock.release()
                                    raise
                        
                else:
                        debug_log("releasing locks in process spool")
                        text_database_lock.release()
                        title_database_lock.release()
                        raise

            debug_log("releasing locks in process spool")
            text_database_lock.release()
            title_database_lock.release()

    debug_log("forcing commit xap transaction (bottom of process spool)")
    force_commit_xapian_transaction()
    debug_log("forced commit successfully")
    req.db_disconnect()
    del req

def load_spool():
    """
    Load spool that was serialized to disk, if it's there.
    """
    global spool
    if os.path.exists('syc_search.spool'):
        spool = cPickle.load(open('syc_search.spool', 'r'))
        os.remove('syc_search.spool')
    return spool

def save_spool():
    """
    Save spool to the disk.
    """
    global spool
    if spool.item_queue: # if there's things in the spool
        cPickle.dump(spool, open('syc_search.spool', 'w'), True)

def servespool():
    global spool_lock, spool, keep_processing, doing_db_rebuild, in_re_init
    spool = load_spool()

    slept = SPOOL_WAIT_TIME
    while keep_processing:
        time.sleep(1)
        slept -= 1
        if slept <= 0:
            spool_lock.acquire()
            if doing_db_rebuild:
                in_re_init = True
            spool_to_process = copy.copy(spool)
            spool.clear()
            spool_lock.release()

            process_spool(spool_to_process) 
            slept = SPOOL_WAIT_TIME
            if in_re_init and not doing_db_rebuild:
                # time to do an automic rename and clean up
                # after the rebuild
                cleanup_db_init()

    save_spool()
      
def serveclient(client):
    def get_wiki():
        wiki_name = data[0]
        if wiki_name == '*':
            wiki_name = None
        return wiki_name

    def handle_add():
        client.close()
        pagename = wikiutil.unquoteFilename(data[0])
        spool_lock.acquire()
        spool.mark_for_add((pagename, wiki_name))
        spool_lock.release()

    def handle_delete():
        client.close()
        pagename = wikiutil.unquoteFilename(data[0])
        spool_lock.acquire()
        spool.mark_for_remove((pagename, wiki_name))
        spool_lock.release()

    def handle_re_init():
        global doing_db_rebuild, tmp_db_location, text_database
        global title_database, text_database_lock, title_database_lock
        client.close()

        spool_lock.acquire()
        spool.clear()
        spool_lock.release()

        timenow = time.time()
        tmp_db_location = os.path.join(os.path.join(config.search_db_location,
                                                    ".."),
                                       "search.%s" % timenow)
        os.mkdir(tmp_db_location)

        # do switchover of title_db and text_db to the temporary location
        doing_db_rebuild = True
        text_database_lock.acquire()
        title_database_lock.acquire()
        del text_database
        del title_database
        text_database, title_database = setup_databases(tmp_db_location)
        text_database_lock.release()
        title_database_lock.release()

    def handle_re_init_stop():
        global doing_db_rebuild, in_re_init
        client.close()
        if not in_re_init:
            in_re_init = True
        doing_db_rebuild = False

    def handle_search():
        lines = data
        p_start_loc = int(data[0])
        t_start_loc = int(data[1])
        terms = cPickle.loads(wikiutil.unquoteFilename(''.join(data[2:])))
        process_search(terms, wiki_name, client, p_start_loc, t_start_loc)
        client.close()
        
    global spool_lock, spool
    wiki_name = None

    input = client.makefile('r', 0)
    type = None
    data = None
    lines = []
    requests = []
    for line in input:
        line = line.strip()
        if not line:
            if type == 'E': # end
                break
            else:
                # reset.  get ready for next request
                requests.append(lines)
                type = None
                lines = []
                continue

        if not type:
            type = line
        lines.append(line)

    for request in requests:
        type = request[0]
        data = request[1:]
        
        if type == 'F':
            wiki_name = get_wiki()
        elif type == 'A':
            handle_add() 
        elif type == 'D':
            handle_delete()  
        elif type == 'S':
            handle_search()
        elif type == 'Is':
            handle_re_init()
        elif type == 'Ie':
            handle_re_init_stop()
        else:
            client.close()
            return "Error with client protocol."

    input.close()


def do_run(host, port):
  global keep_processing
  lstn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  lstn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  lstn.bind((host, port))
  lstn.listen(5)

  # start the spool thread
  threading.Thread(target=servespool).start()

  while True:
      try:
        (clnt, ap) = lstn.accept()
        threading.Thread(target=serveclient, args=(clnt,)).start()
      except KeyboardInterrupt:
         force_commit_xapian_transaction()
         while threading.activeCount() > 2:
           pass # wait for serveclient threads to finish
         keep_processing = False
         break

  lstn.close()

def run_as_daemon(host, port):
  pid = os.fork()
  if pid == 0:
    os.setsid()
    pid = os.fork()
    if pid == 0:
      do_run(host, port)

if __name__ == '__main__':
    global text_database, title_database
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:p:l:d")
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    host = ''
    port = 33432 
    daemon = False
    if opts:
        for o, a in opts:
            if o == '-h':
                host = a
            elif o == '-p':
                port = int(a)
            elif o == '-l':
                db_location = a
            elif o == '-d':
                daemon = True

    if not db_location:
        usage()
        sys.exit(2)

    db_location = os.path.abspath(db_location)

    text_database, title_database = setup_databases()

    if daemon:
        run_as_daemon(host, port)
    else:
        do_run(host, port)
