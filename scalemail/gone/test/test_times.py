from twisted.trial import unittest
import datetime
from scalemail.gone import times

class Parsing(unittest.TestCase):
    def test_day(self):
        i = times.TimeInterval.fromString('2001-02-01 2001-02-03')
        self.assertEquals(i.start, datetime.date(2001, 2, 1))
        self.assertEquals(i.stop, datetime.date(2001, 2, 3))

    def test_hour(self):
        i = times.TimeInterval.fromString('2001-02-01T12 2001-02-01T13')
        self.assertEquals(i.start, datetime.datetime(2001, 2, 1, 12))
        self.assertEquals(i.stop, datetime.datetime(2001, 2, 1, 13))
    test_hour.todo = "mx.DateTime parses T12 as T01:02, and time.strptime doesn't handle timezones"

    def test_minute(self):
        i = times.TimeInterval.fromString('2001-02-01T12:05 2001-02-01T13:58')
        self.assertEquals(i.start, datetime.datetime(2001, 2, 1, 12, 5))
        self.assertEquals(i.stop, datetime.datetime(2001, 2, 1, 13, 58))

    def test_second(self):
        i = times.TimeInterval.fromString('2001-02-01T12:05:43 2001-02-01T13:58:45')
        self.assertEquals(i.start, datetime.datetime(2001, 2, 1, 12, 5, 43))
        self.assertEquals(i.stop, datetime.datetime(2001, 2, 1, 13, 58, 45))

class Contains(unittest.TestCase):
    def test_simple(self):
        i = times.TimeInterval.fromString('2001-02-01T12:05 2001-02-01T13:58')
        self.failUnless(i.start in i)
        self.failUnless(i.stop in i)

        self.failUnless(datetime.datetime(2001, 2, 1, 12, 6) in i)
        self.failUnless(datetime.datetime(2001, 2, 1, 13, 57) in i)

        self.failIf(datetime.datetime(2001, 2, 1, 12, 4) in i)
        self.failIf(datetime.datetime(2001, 2, 1, 13, 59) in i)

class Find(unittest.TestCase):
    def setUp(self):
        self.a = times.TimeInterval.fromString('2001-02-01T12:05 2001-02-01T13:58')
        self.b = times.TimeInterval.fromString('2001-02-02T14:15 2001-02-02T15:58')
        self.c = times.TimeInterval.fromString('2001-02-05T12:00 2001-02-08T13:0')
        self.l = [self.a, self.b, self.c]

    def test_1(self):
        self.assertEquals(times.findTime(datetime.datetime(2001, 2, 1, 13, 50),
                                         self.l),
                          self.a)

    def test_2(self):
        self.assertEquals(times.findTime(datetime.datetime(2001, 2, 2, 14, 50),
                                         self.l),
                          self.b)

    def test_notFound(self):
        self.assertEquals(times.findTime(datetime.datetime(2001, 2, 2, 15, 59),
                                         self.l),
                          None)