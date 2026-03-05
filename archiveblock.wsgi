#!/usr/bin/env python3

import sys
import os, os.path
import stat
import configparser
import logging, logging.handlers
import threading

from tinyapp.handler import ReqHandler
from tinyapp.constants import PLAINTEXT, HTML, BINARY
from tinyapp.excepts import HTTPRawResponse, HTTPError
from blocklib.blockapp import BlockApp

class han_Home(ReqHandler):
    def do_get(self, req):
        rediruri = req.env['REDIRECT_URL']
        if not rediruri.startswith('/'):
            raise HTTPError('404 Not Found', f'Does not start with slash: {pathname}\n')

        pathname = self.app.basepath + rediruri
        
        try:
            fstat = os.stat(pathname)
        except FileNotFoundError:
            raise HTTPError('404 Not Found', f'Unable to stat: {pathname}\n')

        if stat.S_ISDIR(fstat.st_mode):
            raise HTTPError('421 Misdirected Request', f'Plugin cannot handle directory: {pathname}\n')

        filesize = fstat.st_size
        linkheader = None
        safetyheader = None
        
        if req.env['SERVER_NAME'] != self.app.rootdomain:
            linkheader = "<https://%s%s>; rel=\"canonical\"" % (self.app.rootdomain, req.env['REQUEST_URI'],)
        
        blockmap = self.app.get_blockmap()
        tags, redirect = blockmap.get_pair(rediruri)

        if tags:
            safetyheader = tags
            
        if redirect:
            if req.env['SERVER_NAME'] != self.app.restrictdomain:
                # Construct a 302-redirect response to the ukrestrict
                # domain.
                # (Testing indicates we don't need to percent-encode the
                # URI.)
                newurl = "https://%s%s" % (self.app.restrictdomain, req.env['REQUEST_URI'],)
                req.set_status('302 Found')
                req.set_content_type(PLAINTEXT)
                req.add_header('Location', newurl),
                req.add_header('Access-Control-Allow-Origin', '*')
                if linkheader:
                    req.add_header('Link', linkheader)
                if safetyheader:
                    req.add_header('X-IFArchive-Safety', safetyheader)
                yield f'File tagged: {tags}\n'
                yield f'Redirecting to: {newurl}\n'
                return

            # The request came to the ukrestrict domain. Let it proceed
            # with the magic header. (UK geoblocking will happen at the
            # Cloudflare level.)
            
        # At this point we know we are going to return the file contents.
        # We may have tags, but they are not ones that are restricted in
        # the UK. (In this case we'll add the X-IFArchive-Safety header.)
        
        mimetype = self.app.mimemap.get(pathname)
        
        fl = open(pathname, 'rb')
        wrapper = req.env['wsgi.file_wrapper'](fl)
        
        headers = [
            ('Content-Length', str(filesize)),
        ]
        if mimetype:
            headers.append( ('Content-Type', mimetype) )
        if linkheader:
            headers.append( ('Link', linkheader) )
        if safetyheader:
            headers.append( ('X-IFArchive-Safety', safetyheader) )
            
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

