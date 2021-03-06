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

class Stringify(unittest.TestCase):
    def test_simple(self):
        orig = '2001-02-01T12:05 2001-02-01T13:58'
        want = '2001-02-01T12:05:00 2001-02-01T13:58:00'
        t = times.TimeInterval.fromString(orig)
        got = str(t)
        self.assertEquals(got, want)

    def test_day(self):
        orig = '2001-02-01 2001-02-01'
        t = times.TimeInterval.fromString(orig)
        got = str(t)
        self.assertEquals(got, orig)

class Compare(unittest.TestCase):
    def test_equal_different(self):
        s1 = '2001-02-01T12:06 2001-02-01T13:58'
        s2 = '2001-02-01T12:05 2001-02-01T13:58'
        t1 = times.TimeInterval.fromString(s1)
        t2 = times.TimeInterval.fromString(s2)
        self.failIf(t1 == t2)

    def test_equal_self(self):
        orig = '2001-02-01T12:05 2001-02-01T13:58'
        t1 = times.TimeInterval.fromString(orig)
        t2 = times.TimeInterval.fromString(orig)
        self.assertEquals(t1, t2)

    def test_equal_similar(self):
        s1 = '2001-02-01T12:05 2001-02-01T13:58'
        s2 = '2001-02-01T12:05:00 2001-02-01T13:58:00'
        t1 = times.TimeInterval.fromString(s1)
        t2 = times.TimeInterval.fromString(s2)
        self.assertEquals(t1, t2)

    def test_equal_day(self):
        s1 = '2001-02-01 2001-02-01'
        s2 = '2001-02-01T00:00:00 2001-02-01T00:00:00'
        t1 = times.TimeInterval.fromString(s1)
        t2 = times.TimeInterval.fromString(s2)
        self.assertEquals(t1, t2)


    def test_notequal_different(self):
        s1 = '2001-02-01T12:06 2001-02-01T13:58'
        s2 = '2001-02-01T12:05 2001-02-01T13:58'
        t1 = times.TimeInterval.fromString(s1)
        t2 = times.TimeInterval.fromString(s2)
        self.failUnless(t1 != t2)

    def test_notequal_self(self):
        orig = '2001-02-01T12:05 2001-02-01T13:58'
        t1 = times.TimeInterval.fromString(orig)
        t2 = times.TimeInterval.fromString(orig)
        self.failIf(t1 != t2)

    def test_notequal_similar(self):
        s1 = '2001-02-01T12:05 2001-02-01T13:58'
        s2 = '2001-02-01T12:05:00 2001-02-01T13:58:00'
        t1 = times.TimeInterval.fromString(s1)
        t2 = times.TimeInterval.fromString(s2)
        self.failIf(t1 != t2)

    def test_notequal_day(self):
        s1 = '2001-02-01 2001-02-01'
        s2 = '2001-02-01T00:00:00 2001-02-01T00:00:00'
        t1 = times.TimeInterval.fromString(s1)
        t2 = times.TimeInterval.fromString(s2)
        self.failIf(t1 != t2)

class Intersection(unittest.TestCase):
    """
	other  |---|
	1 |---|.   .
	2  |---|   .
	3   |---|  .
        4      |-| .
        5      .|-|.
        6      |---|
        7      . |-|
        8      . |---|
        9      .   |---|
        10     .   . |---|
        11   |-------|
    """
    def setUp(self):
        self.me = times.TimeInterval.fromString(
            '2005-01-09T01:02:03 2005-01-09T03:02:03')

    def check(self, other, want):
        other = times.TimeInterval.fromString(other)
        if want is not None:
            want = times.TimeInterval.fromString(want)
        got = self.me & other
        self.assertEquals(got, want)

    def test_1(self):
        self.check(other='2005-01-09T00:05:00 2005-01-09T01:00:00',
                   want=None)

    def test_2(self):
        self.check(other='2005-01-09T00:05:00 2005-01-09T01:02:03',
                   want='2005-01-09T01:02:03 2005-01-09T01:02:03')

    def test_3(self):
        self.check(other='2005-01-09T00:05:00 2005-01-09T01:03:03',
                   want='2005-01-09T01:02:03 2005-01-09T01:03:03')

    def test_4(self):
        self.check(other='2005-01-09T01:02:03 2005-01-09T02:00:00',
                   want='2005-01-09T01:02:03 2005-01-09T02:00:00')

    def test_5(self):
        self.check(other='2005-01-09T01:30:00 2005-01-09T02:00:00',
                   want='2005-01-09T01:30:00 2005-01-09T02:00:00')

    def test_6(self):
        self.check(other='2005-01-09T01:02:03 2005-01-09T03:02:03',
                   want='2005-01-09T01:02:03 2005-01-09T03:02:03')

    def test_7(self):
        self.check(other='2005-01-09T02:02:03 2005-01-09T03:02:03',
                   want='2005-01-09T02:02:03 2005-01-09T03:02:03')

    def test_8(self):
        self.check(other='2005-01-09T02:02:03 2005-01-09T04:02:03',
                   want='2005-01-09T02:02:03 2005-01-09T03:02:03')

    def test_9(self):
        self.check(other='2005-01-09T03:02:03 2005-01-09T04:02:03',
                   want='2005-01-09T03:02:03 2005-01-09T03:02:03')

    def test_10(self):
        self.check(other='2005-01-09T05:02:03 2005-01-09T06:02:03',
                   want=None)

    def test_11(self):
        self.check(other='2004-01-01 2006-01-01',
                   want='2005-01-09T01:02:03 2005-01-09T03:02:03')

class ChronologicalOrder(unittest.TestCase):
    def test_equal_day(self):
        s = '2001-02-01 2001-02-01'
        t = times.TimeInterval.fromString(s)
        # that's it!

    def test_equal_time(self):
        s = '2001-02-01T12:05 2001-02-01T12:05'
        t = times.TimeInterval.fromString(s)
        # that's it!

    def test_bad_day(self):
        s = '2001-02-02 2001-02-01'
        e = self.assertRaises(times.StartMustPredateStopError,
                              times.TimeInterval.fromString, s)

    def test_bad_time(self):
        s = '2001-02-02T12:05 2001-02-02T12:03'
        e = self.assertRaises(times.StartMustPredateStopError,
                              times.TimeInterval.fromString, s)
