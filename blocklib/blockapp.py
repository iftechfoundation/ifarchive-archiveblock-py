import threading

from tinyapp.app import TinyApp, TinyRequest
from tinyapp.handler import ReqHandler

class BlockApp(TinyApp):
    """BlockApp: The TinyApp class.
    """
    
    def __init__(self, config, hanclasses):
        TinyApp.__init__(self, hanclasses)

        self.blockmappath = config['ArchiveBlock']['ArchiveBlockMapPath']
        self.restrictdomain = config['ArchiveBlock']['ArchiveBlockRestrictDomain']
        
        # Thread-local storage for various things which are not thread-safe.
        self.threadcache = threading.local()
