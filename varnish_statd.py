#!/usr/bin/env python

import time
import os
import socket
from Queue import Queue

import varnishapi


class CarbonClient:

    def __init__(self, host='localhost', port=2003):
        self.host = host
        self.port = port
        self._socket = None
        self.prefix = "server.%s.varnish." % socket.gethostname()

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

wait = int(os.getenv('VARNISH_STATD_WAIT', 10))
carbon = os.getenv('CARBON_HOST', '127.0.0.1')
stats = os.getenv("VARNISH_STATD_STATS", "hitmisspass").split(',')

queue = Queue(100)
while True:
    for n in names:
        ts = int(time.time())
        s = stat(n)
        if len(s) == 0:  # No stat, maybe varnish is down
            # FIXME log that
            continue
        if n is None:
            n = "default"
        if 'hitmisspass' in stats:
            for k in ['cache_hit', 'cache_hitpass', 'cache_miss']:
                v = s['MAIN.%s' % k]
                print("%s: %s" % (k, v))
                queue.put((ts, n, k, v))
    print("Queue size %i" % queue.qsize())
    c = CarbonClient(host=carbon)
    for _ in range(queue.qsize()):
        line = ts, n, k, v = queue.get()
        key = ".".join([n, k])
        try:
            c.send(key, v, ts)
        except socket.error:
            # FIXME log that
            queue.put(line)

    time.sleep(wait)
