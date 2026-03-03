import os
import threading

from tinyapp.app import TinyApp, TinyRequest
from tinyapp.handler import ReqHandler

from .map import parse_blockmap

class BlockApp(TinyApp):
    """BlockApp: The TinyApp class.
    """
    
    def __init__(self, config, hanclasses):
        TinyApp.__init__(self, hanclasses)

        self.blockmappath = config['ArchiveBlock']['ArchiveBlockMapPath']
        self.restrictdomain = config['ArchiveBlock']['ArchiveBlockRestrictDomain']
        
        # Thread-local storage for various things which are not thread-safe.
        self.threadcache = threading.local()

        # Thread lock for checking and reloading the blockmap.
        self.maplock = threading.Lock()

        self.blockmap = None
        self.blockmaptime = 0

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
        
