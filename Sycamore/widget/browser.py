# -*- coding: iso-8859-1 -*-
"""
    Sycamore - DataBrowserWidget

    @copyright: 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

from Sycamore.widget import base


class DataBrowserWidget(base.Widget):

    def __init__(self, request, **kw):
        base.Widget.__init__(self, request, **kw)
        self.data = None

    def setData(self, dataset):
        """ Sets the data for the browser (see Sycamore.util.dataset).
        """
        self.data = dataset

    def toHTML(self, table_attrs={}, append=[]):
        fmt = self.request.formatter

        result = []
        result.append(fmt.table(1, attrs=table_attrs))

        # add header line
        result.append(fmt.table_row(1))
        for col in self.data.columns:
            if col.hidden: continue
            result.append(fmt.table_cell(1))
            result.append(fmt.strong(1))
            result.append(col.label or col.name)
            result.append(fmt.strong(0))
            result.append(fmt.table_cell(0))
        result.append(fmt.table_row(0))

        # add data
        self.data.reset()
        row = self.data.next()
        while row:
            result.append(fmt.table_row(1))
            for idx in range(len(row)):
                if self.data.columns[idx].hidden: continue
                result.append(fmt.table_cell(1))
                result.append(str(row[idx]))
                result.append(fmt.table_cell(0))
            result.append(fmt.table_row(0))
            row = self.data.next()

	# deal with extra appended row, if we want a next/previous thing
	if append:
	    for entry in append:
	      result.append(fmt.table_row(1))
	      result.append(fmt.table_cell(1, attrs={'colspan':len(self.data.columns)}))
	      result.append(entry)
	      result.append(fmt.table_cell(0))
	      result.append(fmt.table_row(0))

        result.append(fmt.table(0))
        return ''.join(result)


    def render(self, attrs={}, append=[]):
        self.request.write(self.toHTML(table_attrs=attrs, append=append))

