#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time

from errno import *
from stat import *

import fuse

import pycavane
import fusqlogger
from memo import Memoized

from threading import Thread


class MegaFile(Thread):
    def __init__ (self, url, cachedir):
        Thread.__init__(self)
        self.url = url
        self.filename = url.rsplit('/', 1)[1]
        self.cachedir = cachedir
        self.cache_file = self.cachedir+'/'+self.filename
        self.released = False
        self.running = True

    @property
    def size(self):
        size = 0
        if os.path.exists(self.cache_file):
            size = os.path.getsize(self.cache_file)
        return size

    def read(self, offset, size):
        fusqlogger.dump('offset: "%s" size: "%s"' % (offset, size), 'READ')
        while offset+size > self.size:
            # EOF
            if not self.running:
                return ''
            time.sleep(1)
            fusqlogger.dump('offset: "%s" size: "%s"' % \
                    (offset+size, self.size), 'WAIT')

        with open(self.cachedir+'/'+self.filename) as fd:
            fd.seek(offset)
            data = fd.read(size)
        return data

    def run(self):
        if not os.path.exists(self.cache_file):
            url = pycavane.get_megalink(self.url)
            handle = pycavane.url_open(url, handle=True)
            fd = open(self.cachedir+'/'+self.filename, 'w')

            while True:
                if self.released:
                    # Remove file from cache if released
                    # before finish the download
                    os.remove(self.cachedir+'/'+self.filename)
                    break
                data = handle.read(1024)
                if not data:
                    fd.close()
                    break
                fd.write(data)
                fd.flush()
        self.running = False


fuse.fuse_python_api = (0, 2)

class Metadata(fuse.Stat):
    @fusqlogger.log()
    def __init__(self, mode, is_dir):
        fuse.Stat.__init__(self)

        if is_dir:
            self.st_mode = S_IFDIR | mode
            self.st_nlink = 2
        else:
            self.st_mode = S_IFREG | mode
            self.st_nlink = 1

        now = int(time.time())
        self.st_atime = now
        self.st_mtime = now
        self.st_ctime = now
        self.st_uid   = os.getuid()
        self.st_gid   = os.getgid()
        #self.st_size  = 0

class FuCavane(fuse.Fuse):
    @fusqlogger.log()
    def __init__(self, *args, **kw):
        fuse.Fuse.__init__(self, *args, **kw)

        self.series = {}
        self.episodes = {}

        root_mode = S_IRUSR|S_IXUSR|S_IWUSR|S_IRGRP|S_IXGRP|S_IXOTH|S_IROTH
        file_mode = S_IRUSR|S_IWUSR|S_IRGRP|S_IROTH

        # Create shared metadata for files and directories
        self.dir_metadata = Metadata(root_mode, True)
        self.file_metadata = Metadata(file_mode, False)

        # Dictionary mapping inode_path -> (size, is_directory)
        self.paths = ['/']


    def main(self):
        Memoized.set_cache_dir(self.cache)

        # Fill with all tables as folders
        for serie in self.get_series():
            # TODO: better path sanitize
            serie_name = serie[1].replace('/', '|')
            serie_path = "/" + serie_name

            self.paths.append(serie_path)

            self.series[serie_path] = serie[0]

        return fuse.Fuse.main(self)

    @Memoized
    def get_series(self):
        return pycavane.get_series()

    @Memoized
    def get_seassons(self, serie):
        return pycavane.get_seassons([serie])

    @Memoized
    def get_subtitle(self, serie):
        return pycavane.get_subtitle([serie])

    @Memoized
    def get_episodes(self, seasson):
        return pycavane.get_episodes([seasson])

    @Memoized
    def get_direct_link(self, episode):
        return pycavane.get_direct_links([episode], 'megaupload')[1]

    @Memoized
    def get_file_size(self, episode):
        ret =  self.get_direct_link(episode)
        fd = pycavane.url_open(ret, handle=True)
        fz = '<strong>File size:</strong> '
        for line in fd:
            if fz in line:
                try:
                    line = line.split(fz)[1].split('<br />', 1)[0]
                    size, measure = line.split(' ')
                    return float(size)*1024*1024
                except Exception, error:
                    print error
                    print 'Sonthing change in MU implementation?'
                    return 0
                break

    @fusqlogger.log()
    def getattr(self, path):
        spath = path.split("/")

        is_dir = len(spath) != 4

        if path in self.paths:
            if is_dir:
                result = self.dir_metadata
            else:
                result = self.file_metadata
                #result.st_size = 1024*1024
                #if path[-3:] == 'mp4':
                    #episode = self.series[path[:-4]]
                    #result.st_size = self.get_file_size(episode)
        else:
            result = -ENOENT

        return result


    @fusqlogger.log()
    def open(self, path, flags):
        if path[-3:] == 'mp4':
            episode = self.series[path[:-4]]
            if episode not in self.episodes:
                ret =  self.get_direct_link(episode)
                self.episodes[episode] = MegaFile(ret, self.cache)
                self.episodes[episode].start()
        return 0

    @fusqlogger.log()
    def read(self, path, size, offset):
        episode = self.series[path[:-4]]

        if path[-3:] == 'srt':
            handle = self.get_subtitle(episode)
        else:
            if episode not in self.episodes:
                raise Exception, 'WTF?'
            handle = self.episodes[episode]
            return handle.read(offset, size)

        return handle[offset:offset+size]

    @fusqlogger.log(showReturn=True)
    def mknod(self, path, mode, rdev):
        return 0

    @fusqlogger.log(showReturn=True)
    def write(self, path, buf, offset, fh=None):
        return 0

    @fusqlogger.log()
    def truncate(self, path, size, fh=None):
        return 0

    @fusqlogger.log()
    def unlink(self, path):
        return 0

    @fusqlogger.log(showReturn=True)
    def rename(self, path_from, path_to):
        return 0

    @fusqlogger.log()
    def chmod(self, path, mode):
        return 0

    @fusqlogger.log()
    def chown(self, path, uid, gid):
        return 0

    @fusqlogger.log()
    def utime(self, path, times):
        return 0

    @fusqlogger.log(showReturn=True)
    def mkdir(self, path, mode):
        return 0

    @fusqlogger.log(showReturn=True)
    def rmdir(self, path):
        return 0

    @fusqlogger.log()
    def readdir(self, path, offset):
        result = ['.', '..']

        spath = path.split('/')

        if len(spath) == 2 and spath[1]:
            seassons = self.get_seassons(self.series[path])
            for i in seassons:
                new_path = path+'/'+i[1]
                if new_path not in self.paths:
                    self.paths.append(new_path)
                self.series[new_path] = i[0]

                yield fuse.Direntry(i[1])
            return

        if len(spath) == 3 and spath[2]:
            episodes = self.get_episodes(self.series[path])
            for i in episodes:
                name = i[2].strip()
                new_path = path+'/'+name
                if new_path not in self.paths:
                    self.paths.append(new_path+'.mp4')
                    self.paths.append(new_path+'.srt')
                self.series[new_path] = i[0]

                yield fuse.Direntry(name+'.mp4')
                yield fuse.Direntry(name+'.srt')
            return


        if path != "/":
            path = path + "/"

        for i in self.paths:
            if i.startswith(path) and i != "/":
                name = i.split(path)[1]
                name = name.split("/")[0]

                if name not in result:
                    result.append(name)

        for i in result:
            yield fuse.Direntry(i)

    @fusqlogger.log()
    def release(self, path, fh=None):
        if path[-3:] == 'mp4':
            episode = self.series[path[:-4]]
            # TODO: handle multiple opens
            if episode in self.episodes:
                self.episodes[episode].released = True
                del(self.episodes[episode])
        return 0

if __name__ == '__main__':
    fs = FuCavane()
    fs.parser.add_option("-c", "--cache", metavar="CACHE",
            default='.', help="[default:.mountpoint]")
    fs.parse(values=fs, errex=1)
    fs.main()
