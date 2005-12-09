import cPickle
f = open('1088084990.24.48504.sessiondict.pickle', 'r')
dict = cPickle.load(f)
for k, v in dict.iteritems():
	print k
	print v
