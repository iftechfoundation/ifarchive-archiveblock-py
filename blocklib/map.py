import re
import os, os.path

class BlockMap:
    def __init__(self, mapfiles, mapdirs, maptrees):
        self.files = mapfiles
        self.dirs = mapdirs
        self.trees = maptrees
        
def parse_blockmap(pathname):
    mapdirs = {}
    maptrees = {}
    mapfiles = {}
    
    with open(pathname) as fl:
        for ln in fl.readlines():
            ln = ln.strip()
            if not ln:
                continue
            if ln.startswith('#'):
                continue
            key, _, tags = ln.partition('\t')
            if not key or not tags:
                raise Exception(f'line is not a def: {ln}')

            key = key.strip()
            tags = tags.strip()
            if ':' not in tags:
                raise Exception(f'block line lacks colon: {tags}')

            if key.endswith('/'):
                raise Exception(f'block line ends with slash: {key}')
            elif key.endswith('/*'):
                key = key[ : -2 ]
                mapdirs[key] = tags
            elif key.endswith('/**'):
                key = key[ : -3 ]
                maptrees[key] = tags
            else:
                mapfiles[key] = tags
                
    return BlockMap(mapfiles, mapdirs, maptrees)


class MIMEMap:
    def __init__(self, map):
        self.map = map

    def get(self, path, default=None):
        dir, suffix = os.path.splitext(path)
        return self.map.get(suffix, default)

def parse_mimemaps(pathnames):
    pat = re.compile(r'^AddType\s+([^ ]+/[^ ]+)\s+(.*)')
    map = {}
    
    for pathname in pathnames:
        with open(pathname) as fl:
            for ln in fl.readlines():
                ln = ln.strip()
                match = pat.match(ln)
                if match:
                    typeval = match.group(1)
                    suffixes = match.group(2)
                    for suffix in suffixes.split():
                        if not suffix.startswith('.'):
                            suffix = '.' + suffix
                        if suffix not in map:
                            map[suffix] = typeval

    return MIMEMap(map)
                
    
