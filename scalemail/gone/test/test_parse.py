from twisted.trial import unittest
import datetime
from scalemail.gone import parse

class Parse(unittest.TestCase):
    def test_only_interval(self):
        r = parse.parse('2001-02-01 2001-02-03')
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertIdentical(r.message, None)
        self.assertEquals(r.settings, {})

    def test_interval_message(self):
        r = parse.parse("""\
2001-02-01 2001-02-03

foo
""")
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertEquals(r.message, 'foo\n')
        self.assertEquals(r.settings, {})

    def test_interval_header_noEmptyLine(self):
        r = parse.parse("""\
2001-02-01 2001-02-03
Subject: add-a-prefix
""")
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertIdentical(r.message, None)
        self.assertEquals(r.settings, {'Subject': 'add-a-prefix'})

    def test_interval_header_emptyLine(self):
        r = parse.parse("""\
2001-02-01 2001-02-03
Subject: add-a-prefix

""")
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertIdentical(r.message, None)
        self.assertEquals(r.settings, {'Subject': 'add-a-prefix'})

    def test_interval_header_message(self):
        r = parse.parse("""\
2001-02-01 2001-02-03
Subject: add-a-prefix

foo
""")
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertEquals(r.message, 'foo\n')
        self.assertEquals(r.settings, {'Subject': 'add-a-prefix'})

class Contains(unittest.TestCase):
    def test_contains(self):
        r = parse.parse("""\
2001-02-01 2001-02-03
Subject: add-a-prefix
""")
        self.failIf(datetime.date(2001, 1, 31) in r)
        self.failUnless(datetime.date(2001, 2, 1) in r)
        self.failUnless(datetime.date(2001, 2, 2) in r)
        self.failUnless(datetime.date(2001, 2, 3) in r)
        self.failIf(datetime.date(2001, 2, 4) in r)
