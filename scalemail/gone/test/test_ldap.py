from twisted.trial import unittest, util
from twisted.internet import defer
import datetime
from ldaptor import entry
from scalemail.gone import ldap

class FakeConnectedLDAPEntry(entry.BaseLDAPEntry):
    def fetch(self, *attributes):
        return defer.succeed(self)
        

class LDAP(unittest.TestCase):
    def setUp(self):
        self.e = FakeConnectedLDAPEntry(dn='cn=foo,dc=example,dc=com',
                                        attributes={
            'cn': ['foo'],
            'bar': ['baz'],
            'scaleMailAway': [
            """\
2001-02-01 2001-02-03

foo
""",
            """\
2001-02-05 2001-02-07
Subject: add-a-prefix
"""],
            })
        
    def test_inactive(self):
        now = datetime.date(2001, 1, 31)
        d = ldap.is_active(self.e, now)
        r = util.deferredResult(d)
        self.assertEquals(r, None)

    def test_active_1(self):
        now = datetime.date(2001, 2, 2)
        d = ldap.is_active(self.e, now)
        r = util.deferredResult(d)
        self.failIfIdentical(r, None)
        self.assertEquals(r.settings, {})
        self.assertEquals(r.message, "foo\n")

    def test_active_2(self):
        now = datetime.date(2001, 2, 5)
        d = ldap.is_active(self.e, now)
        r = util.deferredResult(d)
        self.failIfIdentical(r, None)
        self.assertEquals(r.settings, {'Subject': 'add-a-prefix'})
        self.assertEquals(r.message, None)
