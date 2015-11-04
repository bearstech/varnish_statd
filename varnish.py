import varnishapi


def stat(name):
    vsc = varnishapi.VarnishStat(opt=["-n", name])
    r = vsc.getStats()
    values = dict(((k, v['val']) for k, v in r.iteritems()))
    vsc.Fini()
    return values


try:
    import collectd
except ImportError:
    # we're not running inside collectd
    # it's ok
    pass
else:

    def logger(t, msg):
        if t == 'err':
            collectd.error('%s: %s' % (NAME, msg))
        elif t == 'warn':
            collectd.warning('%s: %s' % (NAME, msg))
        elif t == 'info':
            collectd.info('%s: %s' % (NAME, msg))
        else:
            collectd.notice('%s: %s' % (NAME, msg))

    NAME = "varnish"

    def config_callback(conf):
        for node in conf.children:
            for child in node.children:
                pass


"""
MAIN.cache_hit: 924
MAIN.cache_hitpass: 0
MAIN.cache_miss: 79
"""


if __name__ == "__main__":
    import sys
    from collections import OrderedDict

    for n in sys.argv[1:]:
        values = OrderedDict(sorted(stat(n).items()))
        for k, v in values.iteritems():
            print("%s: %i" % (k, v))
