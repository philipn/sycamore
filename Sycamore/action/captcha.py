# -*- coding: iso-8859-1 -*-
"""
    Sycamore - captcha action

    This action sends and generates CAPTCHAS to test if someone is human

    @copyright: 2006 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import config, wikidb
from Sycamore.Page import Page
import random, time, mimetypes, cStringIO, tempfile, os

do_email_auth = True
actname = __name__.split('.')[-1]

CAPTCHA_VALID_TIME = 60*2 # evil porn captcha bait!!11 (how long is our captcha image good for?)

def send_captcha(page, wikiname, action, auth_code, type):
    captcha = Captcha(page)
    generated = captcha.generate(type=type)
    if captcha.type == 'png':
        audio_url = '%s?action=%s&wikiname=%s&code=%s&audio=1' % (page.url(), action, wikiname, auth_code)
        msg = """<p>%s</p><p>What numbers are in the above distorted image?: <form method="POST" action="%s"><input type="hidden" name="action" value="%s"><input type="hidden" name="code" value="%s"><input type="hidden" name="wikiname" value="%s"><input type="text" size="13" name="captcha_code"/><input type="hidden" name="captcha_id" value="%s"/> <input type="submit" name="save" value="Save"/></form><p>Can't see the image? <a href="%s">Do audio verification.</a></p>""" % (captcha.link(), page.url(), action, auth_code, wikiname, captcha.id, audio_url)
        page.send_page(msg=msg)
    elif captcha.type == 'wav':
        image_url = '%s?action=%s&wikiname=%s&code=%s' % (page.url(), action, wikiname, auth_code)
        msg = """<p>%s</p><p>What numbers do you hear in the above sound?: <form method="POST" action="%s"><input type="hidden" name="action" value="%s"><input type="hidden" name="code" value="%s"><input type="hidden" name="wikiname" value="%s"><input type="text" size="13" name="captcha_code"/><input type="hidden" name="captcha_id" value="%s"/> <input type="submit" name="save" value="Save"/></form><p>Can't hear the audio? <a href="%s">Do image verification.</a></p>""" % (captcha.link(), page.url(), action, auth_code, wikiname, captcha.id, image_url)
        page.send_page(msg=msg)

def generate_audio(word):
    """
    Generates the audio for the provided string word.

    Uses sox, so you must have sox installed for this to work.

    (This distortion method learned from LiveJournal's LJ::Captcha.pm)
    
    @rtype: string 
    @return: string representing the wav audio file
    """
    tmp_dir = tempfile.mkdtemp(prefix="audio_verify")
    
    # use sox to generate the base speech by combining stored number audio
    args = []
    for number in word:
        args.append(os.path.join(config.data_dir, 'audio', 'speech%s.wav' % number))
    args = [config.sox_location] + args + [os.path.join(tmp_dir, 'tmp.wav')]
    os.spawnl(os.P_WAIT, config.sox_location, *args)
    os.rename(os.path.join(tmp_dir, 'tmp.wav'), os.path.join(tmp_dir, 'speech.wav')) 
    
    # do sox distortions
    os.spawnl(os.P_WAIT, config.sox_location, config.sox_location,
        '-r', '44100', os.path.join(tmp_dir, 'speech.wav'), os.path.join(tmp_dir, 'tmp.wav'),
        'reverb', '0.5', '210', '100', '60',
        'echo', '1', '0.7', '100', '0.03', '400', '0.11')
    os.rename(os.path.join(tmp_dir, 'tmp.wav'), os.path.join(tmp_dir, 'speech.wav')) 
    vibro_amount = str(random.randint(3,9))
    os.spawnl(os.P_WAIT, config.sox_location, config.sox_location,
        '-r', '44100', os.path.join(tmp_dir, 'speech.wav'), os.path.join(tmp_dir, 'noise.wav'),
        'synth', 'brownnoise', '0',
        'vibro', vibro_amount, '0.8',
        'vol', '0.1')
    os.spawnl(os.P_WAIT, config.sox_location, config.sox_location,
        '-r', '44100', os.path.join(tmp_dir, 'noise.wav'), os.path.join(tmp_dir, 'tmp.wav'),
        'fade', '0.5')
    os.rename(os.path.join(tmp_dir, 'tmp.wav'), os.path.join(tmp_dir, 'noise.wav')) 
    os.spawnl(os.P_WAIT, config.sox_location, config.sox_location,
        '-r', '44100', os.path.join(tmp_dir, 'noise.wav'), os.path.join(tmp_dir, 'tmp.wav'),
        'reverse')
    os.rename(os.path.join(tmp_dir, 'tmp.wav'), os.path.join(tmp_dir, 'noise.wav')) 
    os.spawnl(os.P_WAIT, config.sox_location, config.sox_location,
        '-r', '44100', os.path.join(tmp_dir, 'speech.wav'), os.path.join(tmp_dir, 'tmp.wav'),
        'synth', 'brownnoise', '0',
        'fade', '0.5')
    os.rename(os.path.join(tmp_dir, 'tmp.wav'), os.path.join(tmp_dir, 'noise.wav')) 
    os.spawnl(os.P_WAIT, config.sox_location + 'mix', config.sox_location + 'mix',
        '-v', '4', os.path.join(tmp_dir, 'speech.wav'), os.path.join(tmp_dir, 'noise.wav'),
        '-r', '30000', os.path.join(tmp_dir, 'tmp.wav'))
    os.rename(os.path.join(tmp_dir, 'tmp.wav'), os.path.join(tmp_dir, 'speech.wav')) 
    os.remove(os.path.join(tmp_dir, 'noise.wav'))

    vibro_amount = str(random.randint(3,8))
    vibro_intensity = str(random.uniform(0.5, 0.6))
    os.spawnl(os.P_WAIT, config.sox_location, config.sox_location,
        os.path.join(tmp_dir, 'speech.wav'), os.path.join(tmp_dir, 'tmp.wav'),
        'vibro', vibro_amount, vibro_intensity)
    os.rename(os.path.join(tmp_dir, 'tmp.wav'), os.path.join(tmp_dir, 'speech.wav')) 

    # read in the generated .wav and return it
    f = open(os.path.join(tmp_dir, 'speech.wav'), 'rb')
    audio = ''.join(f.readlines())
    f.close()

    os.remove(os.path.join(tmp_dir, 'speech.wav'))
    os.rmdir(tmp_dir)

    return audio
    
class Captcha(object):
    def __init__(self, page, id=None):
        self.page = page
        self.request = page.request
        self.id = id
        self.human_readable_secret = None
        self.type = None

    def set_id(self, id):
        self.id = id

    def _generate_human_readable(self, random_numbers, type='png'):
        """
        Returns a human readable blob of binary-ness to be eventually seen by a person, we hope.
        """
        from Sycamore.support import Captcha
        from Sycamore.support.Captcha.Visual.Tests import BWGimpy
        if type == 'png':
            save_imagefile = cStringIO.StringIO()
            g = BWGimpy(word=random_numbers)
            i = g.render(size=(200,80))
            i.save(save_imagefile, type, quality=90)
            image_value = save_imagefile.getvalue()
            image_value = wikidb.dbapi.Binary(image_value)
            return image_value
        elif type == 'wav':
            audio_value = generate_audio(word=random_numbers)
            audio_value = wikidb.dbapi.Binary(audio_value)
            return audio_value

    def check(self, given_secret):
        """
        Does given_secret match the secret in the db associated with this captcha?

        Cleans up the captcha from the database afterward, so the captcha cannot be used again.
        """
        self.request.cursor.execute("SELECT secret from captchas where id=%(id)s and written_time > %(timevalid)s", {'id':self.id, 'timevalid':(time.time() - CAPTCHA_VALID_TIME)}) 
        result = self.request.cursor.fetchone()
        if result:
            secret = result[0]
            if (given_secret == secret):
                self._clean_up()
                return True

        return False

    def _clean_up(self):
        """
        Removes captcha from database.
        """
        d = {'id':self.id, 'timevalid':(time.time() - CAPTCHA_VALID_TIME)}
        if self.id:
            self.request.cursor.execute("DELETE from captchas where id=%(id)s", d, isWrite=True)
        # decent place to clear out old expired captchas
        self.request.cursor.execute("DELETE from captchas where written_time <= %(timevalid)s", d, isWrite=True)


    def generate(self, type='png'):
        """
        Generates the captcha/secret and stores it into the database.
        """
        self.type = type
        random_numbers = []
        for i in xrange(0, 5):
            random_numbers.append(str(random.randint(0,9)))
        random_numbers = ''.join(random_numbers)
        
        self.human_readable_secret = self._generate_human_readable(random_numbers, type=type)
        id = '%s%s.%s' % (str(time.time()), str(random.random())[0:26], type)  # fairly unique looking id w/length limited due to machine differences w/time
        d = {'id': id, 'written_time': time.time(),
            'secret': random_numbers, 'human_readable_secret': self.human_readable_secret
            }
        self.request.cursor.execute("INSERT into captchas (id, secret, human_readable_secret, written_time) values (%(id)s, %(secret)s, %(human_readable_secret)s, %(written_time)s)", d, isWrite=True)
        self.id = id
    
        
    def url(self):
        """
        Sends the full URL to the captcha.
        """
        return self.page.url(querystr='action=%s&id=%s' % (actname, self.id))

    def link(self):
        """
        Embeds the captcha.
        """
        url = self.url()
        if self.type == 'png':
            return '<img src="%s"/>' % url
        elif self.type == 'wav':
            return '<a href="%s">Play the sound</a>' % url

def send_human_readable(id, request):
    mimetype = None
    request.cursor.execute("SELECT human_readable_secret from captchas where id=%(id)s and written_time > %(timevalid)s", {'id':id, 'timevalid': (time.time() - CAPTCHA_VALID_TIME)})
    result = request.cursor.fetchone()
    if not result:
        request.http_headers()
        request.write("No captcha for this id?  The captcha could have expired, so you may want to try again.")
        return 
    human_readable = wikidb.binaryToString(result[0])

    mimetype = mimetypes.guess_type(id)[0]
    if not mimetype:
        mimetype = "application/octet-stream"

    request.do_gzip = False
    request.http_headers([("Content-Type", mimetype), ("Content-Length", len(human_readable))])
    #output file
    request.write(human_readable, raw=True)


def execute(pagename, request):
    page = Page(pagename, request)
    msg = None
    form = request.form
    
    if form.has_key('id'):
        id = request.form['id'][0]
        return send_human_readable(id, request)
    return page.send_page(msg=msg)
