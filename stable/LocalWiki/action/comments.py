# Imports
import time, string, thread
from LocalWiki import config, user, util, wikiutil, request
from LocalWiki.logfile import editlog, eventlog
import os
from LocalWiki.PageEditor import PageEditor
from LocalWiki.request import RequestBase
from LocalWiki.user import User

def execute(pagename, request):
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = PageEditor(pagename, request)
    msg = ''
    oldtext = page.get_raw_body()
    everything_is_okay = 0

    # be extra paranoid
    if actname in config.excluded_actions or \
        not request.user.may.edit(pagename):
            msg = _('You are not allowed to edit this page. (An account is needed in most cases)')
    # check to make sure the comment macro is in the page
    
    elif string.find(oldtext,"[[Comments") == -1:
       msg = _('Not allowed to comment on this page')

    # check whether page exists at all
    elif not page.exists():
        msg = _('This page does not exist.')

    #elif 1:
#	msg = _('Comments are <strong>temporarily disabled</strong>.  Just <em>edit the page normally</em> by pressing "Edit".  We\'re fixing things..')

    # check whether the user clicked the delete button
    elif request.form.has_key('button') and \
        request.form.has_key('comment_text') and request.form.has_key('ticket'):
        # check whether this is a valid renaming request (make outside
        # attacks harder by requiring two full HTTP transactions)
        if not _checkTicket(request.form['ticket'][0]):
            msg = _('Please use the comment box on the page to add a comment!')
        else:
	   comment_text = request.form.get('comment_text')[0]
	   if len(comment_text) > 1024:
	         msg = _('Your comment is too long.  Please keep it to 1000 characters or less.')
	   else: 
                 now = time.time()
	         now_formatted = request.user.getFormattedDateTime(now)
	         formatted_comment_text = comment_text + " --" + '["' + request.user.name + '"]'
	         newtext = oldtext + "------" + "\n" + "''" + ''.join(now_formatted) + "'' [[nbsp]] " + formatted_comment_text
	         #mtime = PageEditor._write_file(page,newtext)
	         # Record the changes in the editlog
		 #This is a hack.  Just get the time properly..but this will work for now
		 # lets fork off all this bs
		 #i_am_parent = os.fork()
	         #request_remote_addr = request.remote_addr
		 #request_user_valid = request.user.valid
		 #request_user_id = request.user.id
		 #request__dict__ = request.__dict__
		 #i_am_parent = os.fork()
		 #everything_is_okay = 1
		 #if not i_am_parent:
	         #	msg = _('Your comment has been added')
		 #	return page.send_page(request,msg)
		 #else:
	         #	record(request_remote_addr, request_user_valid, request_user_id, request__dict__, pagename, mtime)
                 #	index(pagename, newtext)
		 	#mail(request, pagename)
		 #	os._exit(0)
		 page.saveText(newtext, '0',
            		comment="Comment added.", action="COMMENT_MACRO")
		 msg = _('Your comment has been added.')
	

    return page.send_page(request, msg )

def record(request_remote_addr, request_user_valid, request_user_id, request__dict__, pagename, now):
    log = editlog.EditLog()
    # need to re-write the add methods so they don't actually need the request objects?
    log.noreq_add(request_remote_addr, request_user_valid, request_user_id, pagename, None, int((str(now).split('.'))[0]),'Comment added.','COMMENT_MACRO')
    log2 = editlog.EditLog(config.data_dir + '/pages/' + wikiutil.quoteFilename(pagename) + '/editlog')
    log2.noreq_add(request_remote_addr, request_user_valid, request_user_id, pagename, None, int((str(now).split('.'))[0]),'Comment added.','COMMENT_MACRO')

    #add event log entry
    #eventlog.EventLog().noreq_add(request__dict__, 'COMMENT_MACRO', {'pagename': pagename})

def mail(request, pagename):
                 	# send notification mails
    #if config.mail_smarthost and kw.get('notify', 0):
                 	#   msg = msg + self._notifySubscribers(kw.get('comment', ''))	
    pg = PageEditor(pagename, request)
    pg.notifySubscribers()
	
def index(pagename, newtext):	 	# update the page index
    os.spawnl(os.P_NOWAIT, config.app_dir + '/add_to_index', config.app_dir + '/add_to_index/', '%s' % wikiutil.quoteWikiname(pagename), '%s' % wikiutil.quoteFilename(newtext))
 
def _createTicket(tm = None):
    """Create a ticket using a site-specific secret (the config)"""
    import sha, time, types
    ticket = tm or "%010x" % time.time()
    digest = sha.new()
    digest.update(ticket)

    cfgvars = vars(config)
    for var in cfgvars.values():
        if type(var) is types.StringType:
            digest.update(repr(var))

    return "%s.%s" % (ticket, digest.hexdigest())


def _checkTicket(ticket):
    """Check validity of a previously created ticket"""
    timestamp = ticket.split('.')[0]
    ourticket = _createTicket(timestamp)
    return ticket == ourticket

