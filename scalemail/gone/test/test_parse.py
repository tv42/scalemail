from twisted.trial import unittest
import datetime
from scalemail.gone import parse

class Parse(unittest.TestCase):
    def test_only_interval(self):
        r = parse.parse('2001-02-01 2001-02-03')
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertEquals(r.message.as_string(unixfrom=False),
                          '\n')
        self.assertEquals(r.settings, {})

    def test_interval_message(self):
        r = parse.parse("""\
2001-02-01 2001-02-03

foo
""")
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertEquals(r.message.as_string(unixfrom=False),
                          '\nfoo\n')
        self.assertEquals(r.settings, {})

    def test_interval_header_noEmptyLine(self):
        r = parse.parse("""\
2001-02-01 2001-02-03
X-Scalemail-Subject-Prefix: add-a-prefix
""")
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertEquals(r.message.as_string(unixfrom=False),
                          '\n')
        self.assertEquals(r.settings, {'subject-prefix': 'add-a-prefix'})

    def test_interval_header_emptyLine(self):
        r = parse.parse("""\
2001-02-01 2001-02-03
X-Scalemail-Subject-Prefix: add-a-prefix

""")
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertEquals(r.message.as_string(unixfrom=False),
                          '\n')
        self.assertEquals(r.settings, {'subject-prefix': 'add-a-prefix'})

    def test_interval_header_emailHeader_emptyLine(self):
        r = parse.parse("""\
2001-02-01 2001-02-03
X-Scalemail-Subject-Prefix: add-a-prefix
Foo: bar

""")
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertEquals(r.message.as_string(unixfrom=False),
                          'Foo: bar\n\n')
        self.assertEquals(r.settings, {'subject-prefix': 'add-a-prefix'})

    def test_interval_header_message(self):
        r = parse.parse("""\
2001-02-01 2001-02-03
X-Scalemail-Subject-Prefix: add-a-prefix

foo
""")
        self.assertEquals(r.interval.start, datetime.date(2001, 2, 1))
        self.assertEquals(r.interval.stop, datetime.date(2001, 2, 3))
        self.assertEquals(r.message.as_string(unixfrom=False),
                          '\nfoo\n')
        self.assertEquals(r.settings, {'subject-prefix': 'add-a-prefix'})

class Contains(unittest.TestCase):
    def test_contains(self):
        r = parse.parse("""2001-02-01 2001-02-03""")
        self.failIf(datetime.date(2001, 1, 31) in r)
        self.failUnless(datetime.date(2001, 2, 1) in r)
        self.failUnless(datetime.date(2001, 2, 2) in r)
        self.failUnless(datetime.date(2001, 2, 3) in r)
        self.failIf(datetime.date(2001, 2, 4) in r)

class Compare(unittest.TestCase):
    def test_equal_different(self):
        g1 = parse.parse("""\
2001-02-01 2001-02-03

foo
""")
        g2 = parse.parse("""\
2001-02-01 2001-02-03

foo2
""")
        self.failIf(g1 == g2)

    def test_equal_self(self):
        s = """\
2001-02-01 2001-02-03

foo
"""
        g1 = parse.parse(s)
        g2 = parse.parse(s)
        self.assertEquals(g1, g2)

    def test_notequal_different_interval(self):
        g1 = parse.parse("""\
2001-02-01 2001-02-03

foo
""")
        g2 = parse.parse("""\
2001-02-01 2001-02-04

foo
""")
        self.failUnless(g1 != g2)

    def test_notequal_different_message(self):
        g1 = parse.parse("""\
2001-02-01 2001-02-03

foo
""")
        g2 = parse.parse("""\
2001-02-01 2001-02-03

foo2
""")
        self.failUnless(g1 != g2)

    def test_notequal_different_settings(self):
        g1 = parse.parse("""\
2001-02-01 2001-02-03
X-Scalemail-Thing: value

foo
""")
        g2 = parse.parse("""\
2001-02-01 2001-02-03
X-Scalemail-Thing: different

foo
""")
        self.failUnless(g1 != g2)

    def test_notequal_self(self):
        s = """\
2001-02-01 2001-02-03

foo
"""
        g1 = parse.parse(s)
        g2 = parse.parse(s)
        self.failIf(g1 != g2)
