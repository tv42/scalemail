import datetime
from mx import DateTime

class TimeInterval(object):
    def __init__(self, start, stop):
        self.start = start
        self.stop = stop
        super(TimeInterval, self).__init__(start, stop)

    def _parse(class_, s):
        secs = DateTime.ISO.ParseDateTimeUTC(s).ticks()
        r = datetime.datetime.fromtimestamp(secs)
        return r
    _parse = classmethod(_parse)

    def fromString(class_, s):
        start, stop = s.split(None, 1)
        start = class_._parse(start)
        stop = class_._parse(stop)
        return class_(start, stop)
    fromString = classmethod(fromString)

    def __contains__(self, time):
        # inclusive so date-only ranges act sanely
        return (time >= self.start and time <= self.stop)

def findTime(now, times):
    for interval in times:
        if now in interval:
            return interval
