import sys
import time
import urllib
import urllib2
import cookielib

class Singleton(object):
    '''Not really singleton but close
    taken from dx https://github.com/dequis/derpbot/blob/master/util.py'''
    instance = None

    def __init__(self):
        if type(self).instance is not None:
            raise TypeError("Already instantiated, use .get()")
        type(self).instance = self

    @classmethod
    def get(cls):
        return cls.instance or cls()


headers = {'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; '\
                           'rv:1.9.2.10) Gecko/20100928 Firefox/3.6.1'}

def retry(callback):
    ''' Retry decorator '''
    def deco(url, *args, **kwargs):
        tried = 0
        while tried < 10:
            try:
                return callback(*args, **kwargs)
            except Exception, error:
                tried += 1
                time.sleep(1)
        error = 'Can\'t download\nerror: "%s"\n args: %s' % \
                            (error, str(args) + str(kwargs))
        raise Exception, error
    return deco


class UrlOpener(object):
    ''' An url opener with cookies support '''
    def __init__(self):
        self.setup_cookies()

    @retry
    def __call__(url, data=None, filename=None, handle=False):
        if data:
            request = urllib2.Request(url, urllib.urlencode(data), headers)
        else:
            request = urllib2.Request(url, headers=headers)
        rc = urllib2.urlopen(request)

        if handle:
            return rc

        if filename:
            local = open(filename, 'wb')

        text = ''
        size = 0
        lastsize = 0

        while True:
            buffer = rc.read(1024)
            if buffer == '':
                break

            if filename:
                size += len(buffer)
                local.write(buffer)
                if (size - 1024*4) > lastsize:
                    sys.stdout.write(str(size/1024) + "kb downloaded...\r")
                    sys.stdout.flush()
                    lastsize = size
            else:
                text += buffer
        if filename:
            local.close()
        return text

    def setup_cookies(self):
        ''' Setup cookies in urllib2 '''
        jar = cookielib.CookieJar()
        handler = urllib2.HTTPCookieProcessor(jar)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)
