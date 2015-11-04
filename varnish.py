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

    varnish_conf = dict()

    def config_callback(conf):
        global varnish_conf
        for node in conf.children:
            cache = None
            if node.key == "Cache":
                cache = node.values[0]
                varnish_conf[cache] = dict()
            else:
                logger('err', "Not a valid block name :%s" % node.key)
                continue
            for child in node.children:
                key = child.key.lower()
                if key in set(['hitmisspass']):
                    varnish_conf[cache][key] = child.values[0]
                else:
                    logger('err', "Invalid key in block %s : %s", (cache, key))
        logger('info', str(varnish_conf))

    def read_callback():
        global varnish_conf
        for cache, conf in varnish_conf.items():
            name = conf.get('name', None)
            if name is None:
                name = cache
            if name == "":  # Setting is 'Name ""' meaning don't specify
                name = None
            logger('info', name)
            s = stat(name)
            if len(s) == 0:
                logger('err', "No stats for %s" % cache)
                continue
            if conf.get('hitmisspass', True):
                for k in ['cache_hit', 'cache_hitpass', 'cache_miss']:
                    val = collectd.Values(plugin=NAME, type="absolute")
                    val.plugin_instance = cache
                    val.type = "absolute"
                    val.type_instance = k
                    val.values = [int(s['MAIN.%s' % k])]
                    val.dispatch()

    collectd.register_config(config_callback)
    collectd.register_read(read_callback)


if __name__ == "__main__":
    import sys
    from collections import OrderedDict

    if len(sys.argv) == 1:
        values = OrderedDict(sorted(stat().items()))
        for k, v in values.iteritems():
            print("%s: %i" % (k, v))
    else:
        for n in sys.argv[1:]:
            values = OrderedDict(sorted(stat(n).items()))
            for k, v in values.iteritems():
                print("%s: %i" % (k, v))
