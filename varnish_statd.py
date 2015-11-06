#!/usr/bin/env python

import time
import os
from pprint import pprint

import varnishapi


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
stats = os.getenv("VARNISH_STATD_STATS", "hitmisspass").split(',')

while True:
    for n in names:
        s = stat(n)
        if 'hitmisspass' in stats:
            for k in ['cache_hit', 'cache_hitpass', 'cache_miss']:
                v = s['MAIN.%s' % k]
                print("%s: %s" % (k, v))
        #pprint(s)
        time.sleep(wait)
