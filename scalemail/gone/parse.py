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
        self.settings = dict(settings)

    def __contains__(self, other):
        return other in self.interval

HEADER_PREFIX = 'x-scalemail-'

def parse(s):
    f = StringIO(s)
    firstLine = f.readline()
    # chomp out any line endings, no matter what kind
    firstLine = firstLine.splitlines()[0]
    ival = times.TimeInterval.fromString(firstLine)

    e = email.message_from_file(f)

    settings = {}
    for k,v in e.items():
        l = k.lower()
        if l.startswith(HEADER_PREFIX):
            name = l[len(HEADER_PREFIX):]
            settings[name] = v
    for name in settings.keys():
        del e[HEADER_PREFIX+name]

    return GoneInfo(interval=ival,
                    message=e,
                    settings=settings)
