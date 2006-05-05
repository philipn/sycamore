# This does the typical formatting for a comment field (as seen in the comments in recent changes, user's statistics, page revision history, etc)

from Sycamore.widget import base

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
	  if self.pagename:
	    link_loc = self.request.getScriptname() + '/' + self.pagename + '?action=Files&do=view&target=' + self.comment
	    self.comment = 'Upload of image <a href="%s">%s</a>.' % (link_loc, self.comment)
	  else:
	    self.comment = "Upload of image '%s'." % self.comment
	elif self.type == 'ATTDEL':
	  if self.pagename: 
	    link_loc = self.request.getScriptname() + '/' + self.pagename + '?action=Files&do=view&target=' + self.comment
	    self.comment = 'Image <a href="%s">%s</a> deleted.' % (link_loc, self.comment)
	  else: 
	    self.comment = "Image '%s' deleted." % self.comment
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
