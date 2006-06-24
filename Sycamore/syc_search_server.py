import sys, socket, getopt, threading, time, copy, os, cPickle
import __init__ # woo hackmagic
sys.path.extend(['/Users/philipneustrom/sycamore_base'])
from Sycamore import request, wikiutil, search
from Sycamore.Page import Page

SPOOL_WAIT_TIME = 5*60 # the amount of time to wait, in seconds, until processing a spool

keep_processing = True

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


spool_lock = threading.Lock()
spool = Spool()

def usage():
    print "usage: syc_search_server -l <location of databases> [-h <host> -p <port> -d]"
    print ""
    print " h : what IP/domain to bind to."
    print " p : what port to use (defaults to 33432)."
    print " l : location of the search directory containing title and text databases."
    print " d : run as daemon."
    print ""

def process_search(terms, client):
    global db_location
    req = request.RequestDummy()
    thesearch = search.XapianSearch(None, req, db_location=db_location, processed_terms=terms)
    thesearch.process()
    results = (thesearch.title_results, thesearch.text_results)
    thesearch_encoded = wikiutil.quoteFilename(cPickle.dumps(results))
    output = client.makefile('w',0)
    output.write(thesearch_encoded)
    output.write("\n")

def process_spool(spool):
    global db_location
    if not spool.item_queue: return
    req = request.RequestDummy()
    timenow = time.time() 
    tmp_db_location = os.path.join(os.path.join(db_location, ".."), "search.%s" % timenow)
    os.mkdir(tmp_db_location)
    while spool.item_queue:
      item = spool.item_queue.pop(0)
      type = spool.item_dict[item]
      page = Page(item, req)
      if type == 'add':
        search.index(page, db_location=tmp_db_location)
      elif type == 'del':
        search.remove(page, db_location=tmp_db_location)
    req.db_disconnect()

    # in POSIX os.rename is atomic
    for filename in os.listdir(os.path.join(tmp_db_location, "title")):
      os.rename(os.path.join(os.path.join(tmp_db_location, "title"), filename), os.path.join(os.path.join(db_location, "title"), filename))

    for filename in os.listdir(os.path.join(tmp_db_location, "text")):
      os.rename(os.path.join(os.path.join(tmp_db_location, "text"), filename), os.path.join(os.path.join(db_location, "text"), filename))

    os.rmdir(os.path.join(tmp_db_location, "title"))
    os.rmdir(os.path.join(tmp_db_location, "text"))
    os.rmdir(os.path.join(tmp_db_location))


def servespool():
    global spool_lock, spool, keep_processing

    slept = SPOOL_WAIT_TIME
    while keep_processing:
      time.sleep(1)
      slept -= 1
      if slept <= 0:
        spool_lock.acquire()
        spool_to_process = copy.copy(spool)
        spool.clear()
        spool_lock.release()

        process_spool(spool_to_process) 
        slept = SPOOL_WAIT_TIME
      
def serveclient(client):
    global spool_lock, spool

    input = client.makefile('r', 0)
    type = None
    lines = []
    for line in input:
      line = line.strip()
      if not line: break

      if not type:
        type = line
      else:
        lines.append(line)
    input.close()


    if type == 'A':
      client.close()
      pagename = wikiutil.unquoteFilename(lines[0])
      spool_lock.acquire()
      spool.mark_for_add(pagename)
      spool_lock.release()
    elif type == 'D':
      client.close()
      pagename = wikiutil.unquoteFilename(lines[0])
      spool_lock.acquire()
      spool.mark_for_remove(pagename)
      spool_lock.release()
    elif type == 'S':
      terms = [ wikiutil.unquoteFilename(line) for line in lines ]
      process_search(terms, client)
      client.close()
    else:
      return "Error with client protocol."
      
    client.close()

db_location = None

def do_run(host, port):
  global keep_processing
  lstn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  lstn.bind((host, port))
  lstn.listen(5)

  # start the spool thread
  threading.Thread(target=servespool).start()

  while True:
      try:
        (clnt, ap) = lstn.accept()
        threading.Thread(target=serveclient, args=(clnt,)).start()
      except KeyboardInterrupt:
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

    if daemon: run_as_daemon(host, port)
    else: do_run(host, port)
