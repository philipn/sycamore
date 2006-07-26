# This does the typical formatting for a comment field (as seen in the comments in recent changes, user's statistics, page revision history, etc)

from Sycamore.widget import base
from Sycamore.wikiutil import quoteWikiname
from Sycamore.wikiutil import isImage

class Comment(base.Widget):
    def __init__(self, request, comment, type, pagename=None):
	self.comment = comment
	self.type = type
	self.pagename = pagename
	base.Widget.__init__(self, request)

    def render(self):
	_ = self.request.getText

	if self.type.find('/REVERT') != -1:
	    # check if it's in version format (default)
	    if self.comment[0] == 'v':
	      given_comment = ''
	      given_comment_start = self.comment.find('c')
	      if given_comment_start and given_comment_start != -1:
	        given_comment = self.comment[given_comment_start+1:]
		version = self.comment[1:given_comment_start]
	      else:
	        version = self.comment[1:]
	      if given_comment:
	        self.comment = "Revert to version %(version)s (%(given_comment)s)." % {'version': version, 'given_comment': given_comment}
	      else:	
	        self.comment = "Revert to version %s." % version
	    else:
	      datestamp = self.request.user.getFormattedDateTime(float(self.comment))
	      self.comment = "Revert to version dated %(datestamp)s." % {'datestamp': datestamp}
	elif self.type == 'ATTNEW':
          if isImage(self.comment): file_type="image"
          else: file_type = "file"
	  if self.pagename:
	    link_loc = self.request.getScriptname() + '/' + quoteWikiname(self.pagename) + '?action=Files&do=view&target=' + self.comment
	    self.comment = 'Upload of %s <a href="%s">%s</a>.' % (file_type, link_loc, self.comment)
	  else:
	    self.comment = "Upload of %s '%s'." % (file_type, self.comment)
	elif self.type == 'ATTDEL':
          if isImage(self.comment): file_type="Image"
          else: file_type = "File"
	  if self.pagename: 
	    link_loc = self.request.getScriptname() + '/' + quoteWikiname(self.pagename) + '?action=Files&do=view&target=' + self.comment
	    self.comment = '%s <a href="%s">%s</a> deleted.' % (file_type, link_loc, self.comment)
	  else: 
	    self.comment = "%s '%s' deleted." % (file_type, self.comment)
	elif self.type == 'DELETE':
	    if self.comment: 
		self.comment = "Page deleted (%s)" % self.comment
	    else: 
		self.comment = "Page deleted (no comment)"
	elif self.type == 'NEWEVENT':
	    self.comment = "Event '%s' posted." % self.comment
	elif self.type == 'SAVEMAP':
	    self.comment = "Map location(s) modified"

	return _(self.comment)
