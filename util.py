#!/usr/bin/env python
# coding: utf-8

import time
import urllib
import urllib2
import cookielib
import functools
from StringIO import StringIO

HEADERS = {
    'User-Agent': 'User-Agent:Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.1 '
                  '(KHTML, like Gecko) Chrome/13.0.772.0 Safari/535.1',
    'Referer': 'http://www.cuevana.tv/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;'}

RETRY_TIMES = 5


def retry(callback):
    """
    Retry decorator.
    """

    @functools.wraps(callback)
    def deco(*args, **kwargs):
        tried = 0
        while tried < RETRY_TIMES:
            try:
                return callback(*args, **kwargs)
            except Exception, error:
                tried += 1
                time.sleep(1)
        error = 'Can\'t download\nerror: "%s"\n args: %s' % \
                            (error, str(args) + str(kwargs))
        raise Exception(error)
    return deco


class UrlOpen(object):
    """
    An url opener with cookies support.
    """

    def __init__(self):
        self.setup_cookies()

    @retry
    def __call__(self, url, data=None, filename=None, handle=False):
        if data:
            request = urllib2.Request(url, urllib.urlencode(data), HEADERS)
        else:
            request = urllib2.Request(url, headers=HEADERS)

        rc = self.opener.open(request)

        # return file handler only
        if handle:
            return rc

        if filename:
            local = open(filename, 'wb')
        else:
            local = StringIO()

        while True:
            buffer = rc.read(1024)
            if buffer == '':
                break

            local.write(buffer)

        if filename:
            local.close()
            return

        local.seek(0)
        #TODO: return a file like object
        return local.read()

    def setup_cookies(self):
        """
        Setup cookies in urllib2.
        """

        jar = cookielib.CookieJar()
        handler = urllib2.HTTPCookieProcessor(jar)
        self.opener = urllib2.build_opener(handler)

url_open = UrlOpen()
