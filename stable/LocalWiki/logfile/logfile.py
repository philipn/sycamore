"""
    LocalWiki basic log stuff

    @license: GNU GPL, see COPYING for details.
"""

from __future__ import generators
import os
from LocalWiki import config

class LineBuffer:
    """
    Reads lines from a file
      self.lines    list of lines (Strings) 
      self.offsets  list of offset for each line
    """
    def __init__(self, file, offset, size, forward=True):
        """
        @param file: open file object
        @param offset: position in file to start from
        @param size: aproximate number of bytes to read
        @param forward : read from offset on or from offset-size to offset
        @type forward: boolean
        """
        if forward:
            file.seek(offset)
            self.lines = file.readlines(size)
            self.__calculate_offsets(offset)
        else:
            if offset < 2* size: begin = 0
            else: begin = offset - size
            file.seek(begin)
            self.lines = file.read(offset-begin).splitlines(True)
            if begin !=0:
                begin = begin + len(self.lines[0])
                self.lines = self.lines[1:]
                # XXX check for min one line read
            self.__calculate_offsets(begin)

        self.len = len(self.lines)

    def __calculate_offsets(self, offset):
        """
        @param offset: offset of the first line
        """
        self.offsets = map(lambda x:len(x), self.lines)
        self.offsets.append(0)
        i = 1
        length = len(self.offsets)
        tmp = offset
        while i < length:
            result = self.offsets[i-1] + tmp
            tmp = self.offsets[i]
            self.offsets[i] =  result
            i = i + 1
        self.offsets[0] = offset

class LogFile:
    """
    .filter: function that gets the values from .parser.
       must return True to keep it or False to remove it
    Overwrite .parser() and .add() to customize this class to
    spezial log files
    """
    def __init__(self, filename, buffer_size=65536):
        """
        @param filename: name of the log file
        @param buffer_size: approx. size of one buffer in bytes
        """
        self.buffer_size = buffer_size
        self.__filename = filename
        self.filter = None
        self.__lineno = 0

    def __iter__(self):
        return self

    def reverse(self):
        """ @rtype: iterator
        """
        self.to_end()
        while 1:
            try:
                result = self.previous()
            except StopIteration:
                return
            yield result

    def lastline(self):
	self.to_end()
	try:
		result = self.previous()
	except StopIteration:
		return
	yield result
            
    def sanityCheck(self):
        """ Check for log file write access.
        @rtype: boolean
        """
        if not os.access(self.__filename, os.W_OK):
            return "The log '%s' is not writable!" % (self.__filename,)
        return None

    def __getattr__(self, name):
        """
        generate some attributes when needed
        """
        if name=="_LogFile__rel_index":
            # starting iteration from begin
            self.__buffer1 = LineBuffer(self._input, 0, self.buffer_size)
            self.__buffer2 = LineBuffer(self._input,
                                        self.__buffer1.offsets[-1],
                                        self.buffer_size)
            self.__buffer = self.__buffer1
            self.__rel_index = 0
            return 0
        elif name == "_input":
            try:
                self._input = open(self.__filename, "r")
            except IOError:
                # XXX this triggers on a fresh installed wiki!
                raise StopIteration
            return self._input
        elif name == "_output":
            self._output = open(self.__filename, 'a')
            try:
                os.chmod(self.__filename, 0666 & config.umask)
            except OSError:
                pass
            return self._output

    def size(self):
        """
        @return: size of logfile in bytes
        @rtype: Int
        """
        import os.path
        try:
            size = os.path.getsize(self.__filename)
        except OSError:
            size = 0
        return size

    def lines(self):
        """
        O(n)
        @return: size of logfile in lines
        @rtype: Int
        """
        try:
            f = open(self.__filename, 'r')
            i = 0
            for line in f:
                i += 1
            f.close()
        except IOError:
            i = 0
        return i

    def date(self):
        import os.path
        return os.path.getmtime(self.__filename)

    def peek(self, lines):
        """
        @param lines: number of lines, may be negative to move backward 
        moves file position by lines.
        @return: True if moving more than to the begining and moving to the end
        or beyond
        @rtype: boolean
        peek adjusts .__lineno if set
        This function is not aware of filters!
        """
        self.__rel_index = self.__rel_index + lines
        while self.__rel_index < 0:
            if self.__buffer == self.__buffer2:
                # change to buffer 1
                self.__buffer = self.__buffer1
                self.__rel_index = self.__rel_index + self.__buffer.len
            else:
                if self.__buffer.offsets[0] == 0:
                    # allready at the beginning of the file
                    # XXX
                    self.__rel_index = 0
                    self.__lineno = 0
                    return True
                else:
                    # load previous lines
                    self.__buffer2 = self.__buffer1
                    self.__buffer1 = LineBuffer(self._input,
                                                self.__buffer2.offsets[0],
                                                self.buffer_size,
                                                forward=False)
                    self.__rel_index = (self.__rel_index +
                                        self.__buffer1.len)
                    self.__buffer = self.__buffer1
                
        while self.__rel_index >= self.__buffer.len:
            if self.__buffer == self.__buffer1:
                # change to buffer 2
                self.__rel_index = self.__rel_index - self.__buffer.len
                self.__buffer = self.__buffer2
            else:
                # try to load next buffer
                tmpbuff = LineBuffer(self._input,
                                     self.__buffer1.offsets[-1],
                                     self.buffer_size)
                if tmpbuff.len==0:
                    # end of file
                    if self.__lineno:
                        self.__lineno = (self.__lineno + lines -
                                         (self.__rel_index -
                                          len(self.__buffer.offsets)))
                    self.__rel_index = len(self.__buffer.offsets)
                    return True
                # shift buffers
                self.__buffer1 = self.__buffer2
                self.__buffer2 = tmpbuff                
                self.__rel_index = self.__rel_index - self.__buffer1.len
        if self.__lineno: self.__lineno += lines
        return False

    def __next(self):
        """get next line already parsed"""
        if self.peek(0): raise StopIteration
        result = self.parser(self.__buffer.lines[self.__rel_index])
        self.peek(1)
        return result

    def next(self):
        """
        @return: next entry
        raises StopIteration at file end
        """
        result = None
        while result == None:
            while result == None:
                result = self.__next()
            if self.filter and not self.filter(result):
                result = None
        return result
    
    def __previous(self):
        if self.peek(-1): raise StopIteration
        return self.parser(self.__buffer.lines[self.__rel_index])

    def previous(self):
        """
        @return: previous entry and moves file position one line back
        raises StopIteration at file begin
        """
        result = None
        while result == None:
            while result == None:
                result = self.__previous()
            if self.filter and not self.filter(result):
                result = None
        return result

    def to_begin(self):
        """moves file position to the begin"""
        if self.__buffer1.offsets[0] != 0:
            self.__buffer1 = LineBuffer(self._input,
                                        0,
                                        self.buffer_size)
            self.__buffer2 = LineBuffer(self._input,
                                        self.__buffer1.offsets[-1],
                                        self.buffer_size)
        self.__buffer = self.__buffer1
        self.__rel_index = 0
        self.__lineno = 0

    def to_end(self):
        """moves file position to the end"""
        self._input.seek(0, 2) # to end of file
        size = self._input.tell()
        if (not self.__buffer2) or (size>self.__buffer2.offsets[-1]):
            self.__buffer2 = LineBuffer(self._input,
                                        size,
                                        self.buffer_size,
                                        forward = False)
            
            self.__buffer1 = LineBuffer(self._input,
                                        self.__buffer2.offsets[0],
                                        self.buffer_size,
                                        forward = False)
        self.__buffer = self.__buffer2
        self.__rel_index = self.__buffer2.len
        self.__lineno = None

    def position(self):
        """return a value containing the actual file position
        this can be converted into a String using backticks and then be rebuild
        For this plain file implementation position is an Integer
        """
        return self.__buffer.offsets[self.__rel_index]
        
    def seek(self, position, line_no=None):
        """ moves file position to an value formerly got from .position() 
        to enabling line counting line_no must be provided
        .seek is much more efficient for moving long distances than .peek
        raises ValueError if position is invalid
        """
        if self.__buffer1.offsets[0] <= position < self.__buffer1.offsets[-1]:
            # position is in .__buffer1 
            self.__rel_index = self.__buffer1.offsets.index(position)
            self.__buffer = self.__buffer1
        elif (self.__buffer2.offsets[0] <= position <
              self.__buffer2.offsets[-1]):
            # position is in .__buffer2
            self.__rel_index = self.__buffer2.offsets.index(position)
            self.__buffer = self.__buffer2
        else:
            # load buffers around position
            self.__buffer1 = LineBuffer(self._input,
                                        position,
                                        self.buffer_size,
                                        forward = False)
            self.__buffer2 = LineBuffer(self._input,
                                        position,
                                        self.buffer_size)
            self.__buffer = self.__buffer2
            self.__rel_index = 0
            # XXX test for valid position
        self.__lineno = line_no

    def line_no(self):
        """@return: the actual line number or None if line number is unknown"""
        return self.__lineno
    
    def calculate_line_no(self):
        """if line number is unknown it is calculated
        by parsing the whole file. This may be expensive.
        """
        self._input.seek(0, 0)
        lines = self._input.read(self.__buffer.offsets[self.__rel_index])
        self.__lineno = len(lines.splitlines())
        return self.__lineno

    def parser(self, line):
        """
        @param line: line as read from file
        @return: parsed line or None on error
        Converts the line from file to program representation
        This implementation uses TAB seperated strings.
        This method should be overwritten by the sub classes.
        """
        return line.split("\t")

    def add(self, *data):
        """
        add line to log file
        This implementation save the values as TAB seperated strings.
        This method should be overwritten by the sub classes.
        """
        line = "\t".join(data)
        self._add(line)
        
    def _add(self, line):
        """
        @param line: flat line
        @type line: String
        write on entry in the log file
        """
        if line != None:
            if line[-1] != '\n': line = line + '\n'
            self._output.write(line)
