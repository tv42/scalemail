from twisted.trial import unittest, util
from twisted.internet import defer
import datetime
from ldaptor import entry
from scalemail.gone import ldap
from scalemail.test import test_util

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
X-Scalemail-Subject-Prefix: add-a-prefix
"""],
            })
        self.config = test_util.ConfigDriver('/foo', {})
        
    def test_inactive(self):
        now = datetime.date(2001, 1, 31)
        r = ldap.is_active(self.config, self.e, now)
        self.assertEquals(r, None)

    def test_active_1(self):
        now = datetime.date(2001, 2, 2)
        r = ldap.is_active(self.config, self.e, now)
        self.failIfIdentical(r, None)
        self.assertEquals(r.settings, {})
        self.assertEquals(r.message, "foo\n")

    def test_active_2(self):
        now = datetime.date(2001, 2, 5)
        r = ldap.is_active(self.config, self.e, now)
        self.failIfIdentical(r, None)
        self.assertEquals(r.settings, {'subject-prefix': 'add-a-prefix'})
        self.assertEquals(r.message, None)
