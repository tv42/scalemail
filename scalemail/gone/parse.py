from cStringIO import StringIO
import email
from scalemail.gone import times

class GoneInfo(object):
    interval = None
    message = None
    settings = None

    def __init__(self, interval, message=None, settings=None, *a, **kw):
        super(GoneInfo, self).__init__(self, *a, **kw)
        self.interval = interval
        if message is not None:
            self.message = message
        if settings is None:
            settings = {}
        self.settings = dict(settings)

    def __contains__(self, other):
        return other in self.interval

    def __repr__(self):
        return '%s(interval=%r, message=%r, settings=%r)' % (
            self.__class__.__name__,
            self.interval,
            self.message.as_string(unixfrom=False),
            self.settings)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.interval == other.interval
                and self.message.as_string(unixfrom=False)
                == other.message.as_string(unixfrom=False)
                and self.settings == other.settings)

    def __ne__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return not (self == other)

HEADER_PREFIX = 'x-scalemail-'

def parseMessage(fp):
    e = email.message_from_file(fp)

    settings = {}
    for k,v in e.items():
        l = k.lower()
        if l.startswith(HEADER_PREFIX):
            name = l[len(HEADER_PREFIX):]
            settings[name] = v
    for name in settings.keys():
        del e[HEADER_PREFIX+name]

    return (e, settings)

def parse(s):
    f = StringIO(s)
    firstLine = f.readline()
    # chomp out any line endings, no matter what kind
    firstLine = firstLine.splitlines()[0]
    ival = times.TimeInterval.fromString(firstLine)

    (msg, settings) = parseMessage(f)
    return GoneInfo(interval=ival,
                    message=msg,
                    settings=settings)
