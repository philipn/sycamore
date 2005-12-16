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
	    if comment[0] == 'v':
	      version = comment[1:]
	      comment = "Revert to version %(version)s." % {'version': version}
	    else:
	      datestamp = request.user.getFormattedDateTime(float(comment))
	      comment = "Revert to version dated %(datestamp)s." % {'datestamp': datestamp}
	elif self.type == 'ATTNEW':
	    comment = "Upload of attachment '%s.'" % comment
	elif self.type == 'ATTDEL':
	    comment = "Attachment '%s' deleted." % comment
	elif self.type == 'DELETE':
	    if comment: 
		comment = "Page deleted: '%s'" % comment
	    else: 
		comment = "Page deleted (no comment)"
	elif self.type == 'NEWEVENT':
	    comment = "Event '%s' posted." % comment
	return _(comment)
