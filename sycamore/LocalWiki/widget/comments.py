from LocalWiki.widget import base

class Comment(base.Widget):
    def __init__(self, request, comment, type):
	self.comment = comment
	self.type = type
	base.Widget.__init__(self, request)

    def render(self):
	_ = self.request.getText

	if self.type.find('/REVERT') != -1:
	    # check if it's in version format (default)
	    if self.comment[0] == 'v':
	      version = self.comment[1:]
	      self.comment = "Revert to version %(version)s." % {'version': version}
	    else:
	      datestamp = self.request.user.getFormattedDateTime(float(self.comment))
	      self.comment = "Revert to version dated %(datestamp)s." % {'datestamp': datestamp}
	elif self.type == 'ATTNEW':
	    self.comment = "Upload of attachment '%s.'" % self.comment
	elif self.type == 'ATTDEL':
	    self.comment = "Attachment '%s' deleted." % self.comment
	elif self.type == 'DELETE':
	    if self.comment: 
		self.comment = "Page deleted: '%s'" % self.comment
	    else: 
		self.comment = "Page deleted (no comment)"
	elif self.type == 'NEWEVENT':
	    self.comment = "Event '%s' posted." % self.comment
	return _(self.comment)
