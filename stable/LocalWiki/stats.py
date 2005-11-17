
import sys
sys.path.extend(['/var/www/lib/new_python_dev','/var/www/html/dev/dwiki_dev'])
from LocalWiki import wikiutil, config
import cPickle
import profile


def exe():
    import hotshot.stats
    stat = hotshot.stats.load("/var/www/html/profile.output")
    stat.strip_dirs()
    stat.sort_stats('time','calls')
    stat.print_stats()


   

#profile.run('exe()')
exe()
