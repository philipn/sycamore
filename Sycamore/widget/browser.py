# -*- coding: utf-8 -*-
"""
    Sycamore - DataBrowserWidget

    @copyright: 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore.widget import base

class DataBrowserWidget(base.Widget):
    def __init__(self, request, **kw):
        base.Widget.__init__(self, request, **kw)
        self.data = None

    def setData(self, dataset):
        """
        Sets the data for the browser (see Sycamore.util.dataset).
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
		item = row[idx]
		if type(item) != unicode and type(item) != str:
                  result.append(unicode(str(item)))
		elif type(item) == str:
                  result.append(item.decode('utf-8'))
                else:
		  result.append(item)

                result.append(fmt.table_cell(0))
            result.append(fmt.table_row(0))
            row = self.data.next()

	# deal with extra appended row, if we want a next/previous thing
	if append:
	    for entry in append:
	        result.append(fmt.table_row(1))
	        result.append(fmt.table_cell(1, attrs={'colspan':
                len(self.data.columns)}))
	        result.append(entry)
	        result.append(fmt.table_cell(0))
	        result.append(fmt.table_row(0))

        result.append(fmt.table(0))
        return ''.join(result)


    def render(self, attrs={}, append=[]):
        self.request.write(self.toHTML(table_attrs=attrs, append=append))
