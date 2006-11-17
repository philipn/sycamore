from popen2 import popen2
r, w = popen2('/Users/philipneustrom/sycamore_base_ritual/Sycamore/support/css_cleaner/css_clean.pl')
w.write('hi there')
w.close()
lines = []
for line in r:
    lines.append(line)
print ''.join(lines)
