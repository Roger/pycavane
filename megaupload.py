import os
import re
import time
from threading import Thread

import logger
import shutil
from util import UrlOpen


megalink_re = re.compile('<a.*?href="(http://.*megaupload.*/files/.*?)"')

url_open = UrlOpen()


class MegaFile(Thread):
    def __init__ (self, url, cachedir):
        Thread.__init__(self)
        self.url = url
        self.filename = url.rsplit('/', 1)[1]
        self.cachedir = cachedir
        self._released = False
        self.running = True

        self._last_read = 0

    def get_megalink(self, link):
        megalink = megalink_re.findall(url_open(link))
        if megalink:
            time.sleep(45)
            return megalink[0]
        return None

    def open(self):
        self._released = False

    def release(self):
        self._released = True

    @property
    def cache_file(self):
        filename = self.cachedir+'/'+self.filename
        if os.path.exists(filename+'.mp4'):
            return filename+'.mp4'
        return filename

    @property
    def size(self):
        size = 0
        if os.path.exists(self.cache_file):
            size = os.path.getsize(self.cache_file)
        return size

    def read(self, offset, size):
        logger.log('offset: "%s" size: "%s"' % (offset, size), 'READ')
        self._last_read = time.time()
        while offset+size > self.size:
            # EOF
            if not self.running:
                return ''
            time.sleep(1)
            logger.log('offset: "%s" size: "%s"' % \
                    (offset+size, self.size), 'WAIT')

        with open(self.cache_file) as fd:
            fd.seek(offset)
            data = fd.read(size)
        return data

    def run(self):
        if not os.path.exists(self.cache_file):
            url = self.get_megalink(self.url)
            if not url:
                logger.log('Cant retrieve megaupload url')
                return
            handle = url_open(url, handle=True)
            fd = open(self.cache_file, 'w')

            while True:
                if self._released and self._last_read < time.time()-30:
                    # Remove file from cache if released
                    # before finish the download
                    # and 30 seconds happend from last read
                    os.remove(self.cache_file)
                    break
                data = handle.read(1024)
                if not data:
                    shutil.move(self.cache_file, self.cache_file+'.mp4')
                    fd.close()
                    break
                fd.write(data)
                fd.flush()
        self.running = False
