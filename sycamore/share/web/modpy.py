# System path configuration
import sys

# Path of the directory where wikiconfig.py is located.
# YOU NEED TO CHANGE THIS TO MATCH YOUR SETUP.
sys.path.insert(0, '/var/www/dwiki')

# Path to MoinMoin package, needed if you installed with --prefix=PREFIX
# or if you did not use setup.py.
## sys.path.insert(0, 'PREFIX/lib/python2.3/site-packages')

# Path of the directory where farmconfig is located (if different).
## sys.path.insert(0, '/path/to/farmconfig')


# Set threads flag, so other code can use proper locking.
# TODO: It seems that modpy does not use threads, so we don't need to
# set it here. Do we have another method to check this?
from Sycamore import config
config.use_threads = 1
del config

from Sycamore.request import RequestModPy

def handler(request):
   moinreq = RequestModPy(request)
   return moinreq.run(request)
