""" Caches tiles to Memcache.

Requires python-memcached:
  http://pypi.python.org/pypi/python-memcached

Example configuration:

  "cache": {
    "name": "Memcache",
    "servers": ["127.0.0.1:11211"],
    "revision": 0,
    "key prefix": "unique-id"
  }

Memcache cache parameters:

  servers
    Optional array of servers, list of "{host}:{port}" pairs.
    Defaults to ["127.0.0.1:11211"] if omitted.

  revision
    Optional revision number for mass-expiry of cached tiles
    regardless of lifespan. Defaults to 0.

  key prefix
    Optional string to prepend to Memcache generated key.
    Useful when running multiple instances of TileStache
    that share the same Memcache instance to avoid key
    collisions. The key prefix will be prepended to the
    key name. Defaults to "".
    

"""
from time import time as _time, sleep as _sleep

try:
    from memcache import Client
except ImportError:
    # at least we can build the documentation
    pass

def tile_key(layer, coord, auth, format, rev, key_prefix):
    """ Return a tile key string.
    """
    name = layer.name()
    tile = '%(zoom)d/%(column)d/%(row)d' % coord.__dict__
    if auth:
        ids = "/".join(str(id) for id in sorted(auth))
        return str('%(key_prefix)s/%(rev)s/%(name)s/%(tile)s/%(ids)s.%(format)s' % locals())
    else:
        return str('%(key_prefix)s/%(rev)s/%(name)s/%(tile)s.%(format)s' % locals())

class Cache:
    """
    """
    def __init__(self, servers=['127.0.0.1:11211'], revision=0, key_prefix=''):
        self.servers = servers
        self.revision = revision
        self.key_prefix = key_prefix

    def lock(self, layer, coord, auth, format):
        """ Acquire a cache lock for this tile.
        
            Returns nothing, but blocks until the lock has been acquired.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, auth, format, self.revision, self.key_prefix)
        due = _time() + layer.stale_lock_timeout
        
        try:
            while _time() < due:
                if mem.add(key+'-lock', 'locked.', layer.stale_lock_timeout):
                    return
                
                _sleep(.2)
            
            mem.set(key+'-lock', 'locked.', layer.stale_lock_timeout)
            return

        finally:
            mem.disconnect_all()
        
    def unlock(self, layer, coord, auth, format):
        """ Release a cache lock for this tile.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, auth, format, self.revision, self.key_prefix)
        
        mem.delete(key+'-lock')
        mem.disconnect_all()
        
    def remove(self, layer, coord, auth, format):
        """ Remove a cached tile.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, auth, format, self.revision, self.key_prefix)
        
        mem.delete(key)
        mem.disconnect_all()
        
    def read(self, layer, coord, auth, format):
        """ Read a cached tile.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, auth, format, self.revision, self.key_prefix)
        
        value = mem.get(key)
        mem.disconnect_all()
        
        return value
        
    def save(self, body, layer, coord, auth, format):
        """ Save a cached tile.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, auth, format, self.revision, self.key_prefix)
        
        mem.set(key, body, layer.cache_lifespan or 0)
        mem.disconnect_all()
