# Imports
import time, string, thread
from Sycamore import config, user, util, wikiutil, request
import os
from Sycamore.PageEditor import PageEditor
from Sycamore.request import RequestBase
from Sycamore.user import User

def execute(pagename, request):
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = PageEditor(pagename, request)
    msg = ''
    oldtext = page.get_raw_body()
    everything_is_okay = 0

    # be extra paranoid
    if actname in config.excluded_actions or \
        not request.user.may.edit(page):
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
        request.form.has_key('comment_text'):
        # check whether this is a valid renaming request (make outside
        # attacks harder by requiring two full HTTP transactions)
	comment_text = request.form.get('comment_text')[0]
	if len(comment_text) > 1024:
	      msg = _('Your comment is too long.  Please keep it to 1000 characters or less.')
	else: 
              if request.user.anonymous:
                  userId = request.user.ip
              else:
                  userId = '["' + request.user.name + '"]'

              now = time.time()
	      now_formatted = request.user.getFormattedDateTime(now, global_time=True)
	      formatted_comment_text = comment_text + " --" + userId
	      newtext = oldtext + "------" + "\n" + "''" + ''.join(now_formatted) + "'' [[nbsp]] " + formatted_comment_text
	      page.saveText(newtext, '0',
         		comment="Comment added.", action="COMMENT_MACRO")
	      msg = _('Your comment has been added.')
	

    return page.send_page(msg)
