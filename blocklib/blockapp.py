import os
import threading

from tinyapp.app import TinyApp, TinyRequest
from tinyapp.handler import ReqHandler

from .map import parse_blockmap, parse_mimemaps

class BlockApp(TinyApp):
    """BlockApp: The TinyApp class.
    """
    
    def __init__(self, config, hanclasses):
        TinyApp.__init__(self, hanclasses)

        self.blockmappath = config['ArchiveBlock']['MapPath']
        self.rootdomain = config['ArchiveBlock']['RootDomain']
        self.restrictdomain = config['ArchiveBlock']['RestrictDomain']
        self.mimepaths = config['ArchiveBlock']['MIMEPaths']
        self.basepath = config['ArchiveBlock']['BasePath']
        
        # Thread-local storage for various things which are not thread-safe.
        self.threadcache = threading.local()

        # Thread lock for checking and reloading the blockmap.
        self.maplock = threading.Lock()

        self.blockmap = None
        self.blockmaptime = 0

        pathls = [ val.strip() for val in self.mimepaths.split(',') ]
        self.mimemap = parse_mimemaps(pathls)
        self.loginfo(None, f'Read MIME: {len(self.mimemap.map)} suffixes')

    def get_blockmap(self):
        with self.maplock:
            stat = os.stat(self.blockmappath)
            if self.blockmap and stat.st_mtime == self.blockmaptime:
                return self.blockmap
            newblockmap = parse_blockmap(self.blockmappath)
            self.loginfo(None, f'Read map: {len(newblockmap.files)} files, {len(newblockmap.dirs)} dirs, {len(newblockmap.trees)} trees')
            self.blockmaptime = stat.st_mtime
            self.blockmap = newblockmap
            return self.blockmap
        
