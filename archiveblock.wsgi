#!/usr/bin/env python3

import sys
import os
import configparser
import logging, logging.handlers
import threading

from tinyapp.handler import ReqHandler
from tinyapp.constants import PLAINTEXT, HTML, BINARY
from tinyapp.excepts import HTTPRawResponse, HTTPError
from blocklib.blockapp import BlockApp

class han_Home(ReqHandler):
    def do_get(self, req):
        if False:
            req.set_content_type('text/plain; charset=utf-8')
            yield 'REQUEST_URI: ' + req.env['REQUEST_URI'] + '\n'
            yield 'REDIRECT_URL: ' + req.env['REDIRECT_URL'] + '\n'
            #for key, val in sorted(req.env.items()):
            #    yield '  %s: %s\n' % (key, val,)
            return

        blockmap = self.app.get_blockmap()

        pathname = '/opt/homebrew/var/www'+req.env['REDIRECT_URL']
        try:
            stat = os.stat(pathname)
        except FileNotFoundError:
            raise HTTPError('404 Not Found', f'Unable to stat {pathname}\n')

        mimetype = self.app.mimemap.get(pathname)
        
        fl = open(pathname, 'rb')
        wrapper = req.env['wsgi.file_wrapper'](fl)
        
        headers = [
            ('Content-Length', str(stat.st_size)),
        ]
        if mimetype:
            headers.append( ('Content-Type', mimetype) )
            
        raise HTTPRawResponse('200 OK', headers, wrapper)

# We only have one handler.
handlers = [
    ('', han_Home),
]

appinstance = None
config = None
initlock = threading.Lock()

def create_appinstance(environ):
    global config, appinstance

    with initlock:
        # To be extra careful, we do this under a thread lock. (I don't know
        # if application() can be called by two threads at the same time, but
        # let's assume it's possible.)
        
        if appinstance is not None:
            # Another thread did all the work while we were grabbing the lock!
            return

        # The config file contains all the paths and settings used by the app.
        # The location is specified by the IFARCHIVE_CONFIG env var (if
        # on the command line) or the "SetEnv IFARCHIVE_CONFIG" line (in the
        # Apache WSGI environment).
        configpath = '/var/ifarchive/lib/ifarch.config'
        configpath = environ.get('IFARCHIVE_CONFIG', configpath)
        if not os.path.isfile(configpath):
            raise Exception('Config file not found: ' + configpath)
        
        config = configparser.ConfigParser()
        config.read(configpath)
        
        # Set up the logging configuration.
        # (WatchedFileHandler allows logrotate to rotate the file out from
        # under it.)
        logfilepath = config['ArchiveBlock']['LogFile']
        loghandler = logging.handlers.WatchedFileHandler(logfilepath)
        logging.basicConfig(
            format = '[%(levelname).1s %(asctime)s] %(message)s',
            datefmt = '%b-%d %H:%M:%S',
            level = logging.INFO,
            handlers = [ loghandler ],
        )
        
        # Create the application instance itself.
        appinstance = BlockApp(config, handlers)

    # Thread lock is released when we exit the "with" block.


def application(environ, start_response):
    """The exported WSGI entry point.
    Normally this would just be appinstance.application, but we need to
    wrap that in order to call create_appinstance().
    """
    if appinstance is None:
        create_appinstance(environ)
    return appinstance.application(environ, start_response)

