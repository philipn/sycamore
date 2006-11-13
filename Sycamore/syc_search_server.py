import sys, socket, getopt, threading, time, copy, os, cPickle
import __init__ # woo hackmagic
__directory__ = os.path.dirname(__file__)
share_directory = os.path.abspath(os.path.join(__directory__, '..', 'share'))
sys.path.extend([share_directory]),
from Sycamore import request, wikiutil, search
from Sycamore.Page import Page

SPOOL_WAIT_TIME = 10 # the amount of time to wait, in seconds, until processing a spool

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

def process_search(terms, wiki_name, client, p_start_loc, t_start_loc):
    global db_location
    req = request.RequestDummy()
    if wiki_name:
        req.switch_wiki(wiki_name)
        wiki_global = False
    else:
        wiki_global = True
    thesearch = search.XapianSearch(None, req, db_location=db_location, processed_terms=terms, wiki_global=wiki_global,
        p_start_loc=p_start_loc, t_start_loc=t_start_loc)
    thesearch.process()
    results = (thesearch.title_results, thesearch.text_results)
    thesearch_encoded = wikiutil.quoteFilename(cPickle.dumps(results))
    output = client.makefile('w',0)
    output.write(thesearch_encoded)
    output.write("\n\nE\n\n")

def process_spool(spool):
    global db_location
    if not spool.item_queue: return
    req = request.RequestDummy()
    #timenow = time.time() 
    #tmp_db_location = os.path.join(os.path.join(db_location, ".."), "search.%s" % timenow)
    #os.mkdir(tmp_db_location)
    while spool.item_queue:
        item = spool.item_queue.pop(0)
        type = spool.item_dict[item]
        pagename, wiki_name = item
        if wiki_name:
            page = Page(pagename, req, wiki_name=wiki_name)
        else:
            page = Page(pagename, req)

        if type == 'add':
            search.index(page, db_location=db_location)
        elif type == 'del':
            search.remove(page, db_location=db_location)
    req.db_disconnect()

    # in POSIX os.rename is atomic
    #for filename in os.listdir(os.path.join(tmp_db_location, "title")):
    #  os.rename(os.path.join(os.path.join(tmp_db_location, "title"), filename), os.path.join(os.path.join(db_location, "title"), filename))

    #for filename in os.listdir(os.path.join(tmp_db_location, "text")):
    #  os.rename(os.path.join(os.path.join(tmp_db_location, "text"), filename), os.path.join(os.path.join(db_location, "text"), filename))

    #os.rmdir(os.path.join(tmp_db_location, "title"))
    #os.rmdir(os.path.join(tmp_db_location, "text"))
    #os.rmdir(os.path.join(tmp_db_location))

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
    global spool_lock, spool, keep_processing

    spool = load_spool()

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

    def handle_search():
        lines = data
        p_start_loc = int(data[0])
        t_start_loc = int(data[1])
        terms = [ wikiutil.unquoteFilename(word) for word in data[2:] ]
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
        else:
            client.close()
            return "Error with client protocol."

    input.close()

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
