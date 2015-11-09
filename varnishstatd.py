#!/usr/bin/env python

import time
import os
import socket
from Queue import Queue

import varnishapi


class CarbonClient(object):

    def __init__(self, host='localhost', port=2003):
        self.host = host
        self.port = port
        self._socket = None
        self.prefix = "servers.%s.localhost.varnish." % socket.gethostname()

    @property
    def _lazy_socket(self):
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self.host, self.port))
        return self._socket

    def send(self, key, value, ts=None):
        if ts is None:
            ts = int(time.time())
        line = u"%s.%s %d %d\n" % (self.prefix, key,
                                   value,
                                   ts
                                   )
        self._lazy_socket.sendall(line)


def stat(name=None):
    if name is None:
        vsc = varnishapi.VarnishStat()
    else:
        vsc = varnishapi.VarnishStat(opt=["-n", name])
    r = vsc.getStats()
    values = dict(((k, v['val']) for k, v in r.iteritems()))
    vsc.Fini()
    return values

names = os.getenv('VARNISH_STATD_NAMES')
if names:
    names = names.split(',')
else:
    names = (None,)

wait = int(os.getenv('VARNISH_STATD_WAIT', 60))
carbon = os.getenv('CARBON_HOST', '127.0.0.1')
stats = os.getenv("VARNISH_STATD_STATS",
                  "cache,backend,object,purge,vsm").split(',')

queue = Queue(500)
while True:
    for n in names:
        ts = int(time.time())
        s = stat(n)
        if len(s) == 0:  # No stat, maybe varnish is down
            # FIXME log that
            continue
        if n is None:
            n = "default"
        main_keys = []
        if 'cache' in stats:
            main_keys.append(('cache', ['cache_hit', 'cache_hitpass',
                                        'cache_miss']))
        if 'backend' in stats:
            main_keys.append(('backend', ['backend_conn', 'backend_unhealthy',
                                          'backend_busy', 'backend_fail',
                                          'backend_reuse', 'backend_toolate',
                                          'backend_recycle', 'backend_retry']))
        if 'object' in stats:
            main_keys.append(('object', ['n_object', 'n_vampireobject',
                                         'n_objectcore', 'n_objecthead',
                                         'n_waitinglist', 'n_expired',
                                         'n_lru_nuked', 'n_lru_moved']))
        if 'purge' in stats:
            main_keys.append(('purge', ['n_purges', 'n_obj_purged']))
        if 'vsm' in stats:
            main_keys.append(('vsm', ['vsm_free', 'vsm_used', 'vsm_cooling',
                                      'vsm_overflow', 'vsm_overflowed']))
        for category, keys in main_keys:
            for k in keys:
                v = s['MAIN.%s' % k]
                print("%s %s: %s" % (n, k, v))
                queue.put((ts, n, category, k, v))

    print("Queue size %i" % queue.qsize())
    c = CarbonClient(host=carbon)
    for _ in range(queue.qsize()):
        line = ts, n, category, k, v = queue.get()
        key = ".".join([n, category, k])
        try:
            c.send(key, v, ts)
        except socket.error:
            # FIXME log that
            queue.put(line)

    time.sleep(wait)
