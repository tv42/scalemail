import datetime, time

class InvalidTimeFormatError(Exception):
    """Invalid time interval format"""
    def __str__(self):
        return '%s: %r' % (self.__doc__, ', '.join(self.args))

class StartMustPredateStopError(Exception):
    """Start time must be before stop time"""
    def __str__(self):
        return '%s: %s > %s' % (self.__doc__, self.args[0], self.args[1])

class TimeInterval(object):
    start = None
    stop = None

    def _timify(self, t):
        """Convert a date to datetime, for comparison."""
        if (isinstance(t, datetime.date)
            and not isinstance(t, datetime.datetime)):
            t = datetime.datetime.combine(t, datetime.time())
        return t

    def __init__(self, start, stop):
        if self._timify(start) > self._timify(stop):
            raise StartMustPredateStopError, (start, stop)
        self.start = start
        self.stop = stop
        super(TimeInterval, self).__init__(start, stop)

    def _datetime(class_, t):
        r = datetime.datetime(year=t.tm_year,
                              month=t.tm_mon,
                              day=t.tm_mday,
                              hour=t.tm_hour,
                              minute=t.tm_min,
                              second=t.tm_sec)
        return r
    _datetime = classmethod(_datetime)

    def _date(class_, t):
        r = datetime.date(year=t.tm_year,
                          month=t.tm_mon,
                          day=t.tm_mday)
        return r
    _date = classmethod(_date)

    def _parse(class_, s):
        FORMATS = [
            # ISO (-inspired)
            ('%Y-%m-%dT%H:%M:%S', class_._datetime),
            ('%Y-%m-%dT%H:%M', class_._datetime),
            ('%Y-%m-%dT%H', class_._datetime),
            ('%Y-%m-%d', class_._date),
            ]

        for fmt, mangle in FORMATS:
            try:
                when = time.strptime(s, fmt)
            except:
                pass
            else:
                r = mangle(when)
                return r
        raise InvalidTimeFormatError, s
    _parse = classmethod(_parse)

    def fromString(class_, s):
        start, stop = s.split(None, 1)
        start = class_._parse(start)
        stop = class_._parse(stop)
        return class_(start, stop)
    fromString = classmethod(fromString)

    def __contains__(self, time):
        # inclusive so date-only ranges act sanely
        t = self._timify(time)
        return (t >= self._timify(self.start)
                and t <= self._timify(self.stop))

    def __str__(self):
        return '%s %s' % (self.start.isoformat(),
                          self.stop.isoformat())

    def __repr__(self):
        return '%s(start=%r, stop=%r)' % (
            self.__class__.__name__,
            self.start,
            self.stop)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        if (self._timify(self.start) == self._timify(other.start)
            and self._timify(self.stop) == self._timify(other.stop)):
            return True
        else:
            return False

    def __ne__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        if (self._timify(self.start) != self._timify(other.start)
            or self._timify(self.stop) != self._timify(other.stop)):
            return True
        else:
            return False

    def __and__(self, other):
        """Intersection of two times.

        @return: The intersection or None if the intervals do not
        intersect.

        @rtype: TimeInterval or None
        """
        if not isinstance(other, self.__class__):
            return NotImplemented

        start = max(
            self._timify(self.start),
            self._timify(other.start))
        stop = min(
            self._timify(self.stop),
            self._timify(other.stop))
        if start > stop:
            return None
        return self.__class__(start, stop)

def findTime(now, times):
    for interval in times:
        if now in interval:
            return interval
