from twisted.trial import unittest
from twisted.trial import util as testutil
from twisted.internet import defer
import os
from scalemail import virtual, config, util
from ldaptor import entry

class ConfigDriver(config.ScalemailConfig):
    configFiles = []
    def __init__(self, spool):
        config.ScalemailConfig.__init__(self)
        self.config.set('Scalemail', 'spool', spool)

class VirtualMapFactoryDriver(virtual.ScalemailVirtualMapFactory):
    def __init__(self, accounts={}, *a, **kw):
        virtual.ScalemailVirtualMapFactory.__init__(self, *a, **kw)
        self.__accounts = accounts

    def _getAccount(self, config, local, domain):
        accounts = self.__accounts.get((local, domain), [])
        d = defer.succeed(accounts)

        def _searchCompleted(entries):
            if len(entries) < 1:
                raise util.ScaleMailAccountNotFound
            if len(entries) > 1:
                raise util.ScaleMailAccountMultipleEntries
            e = entries[0]
            return e
        d.addCallback(_searchCompleted)

        return d

class TestVirtual(unittest.TestCase):
    def setUp(self):
        self.spool = self.mktemp()
        os.mkdir(self.spool)
        os.mkdir(os.path.join(self.spool, 'example.com'))
        self.config = ConfigDriver(self.spool)
        self.map = VirtualMapFactoryDriver(config=self.config,
                                           accounts={
            ('foo', 'example.com'):  [entry.BaseLDAPEntry(dn='cn=foo,dc=example,dc=com',
                                                          attributes={ 'scaleMailHost': ['h1'],
                                                                       }),
                                      ],
            ('multiple', 'example.com'):  [1, 2],
            })
                                           
        
    def test_map_domainOnly_notExist(self):
        self.assertEquals(self.map.get('not-exist'),
                          None)

    def test_map_domainOnly_exists(self):
        self.assertEquals(self.map.get('example.com'),
                          'DOMAINEXISTS')

    def test_map_domainOnly_hasBox(self):
        self.assertEquals(self.map.get('foo.scalemail.example.com'),
                          None)

    def test_map_domainOnly_hasBox_nonExist(self):
        # even for non-existing domains
        self.assertEquals(self.map.get('foo.scalemail.not-exist'),
                          None)

    def test_map_hasUser_nonExistingDomain(self):
        self.assertEquals(self.map.get('foo@not-exist'),
                          None)

    def test_map_hasUser_hasBox_nonExistingDomain(self):
        self.assertEquals(self.map.get('foo@bar.scalemail.not-exist'),
                          None)

    def test_map_hasUser_noBox_nonExistingDomain(self):
        self.assertEquals(self.map.get('foo@not-exist'),
                          None)

    def test_map_hasUser_hasBox_validDomain(self):
        self.assertEquals(self.map.get('foo@bar.scalemail.example.com'),
                          None)

    def test_map_hasUser_noBox_validDomain_validUser(self):
        d = self.map.get('foo@example.com')
        r = testutil.wait(d)
        self.assertEquals(r, 'foo@h1.scalemail.example.com')

    def test_map_hasUser_noBox_validDomain_noUser(self):
        d = self.map.get('bar@example.com')
        r = testutil.wait(d)
        self.assertEquals(r, None)

    def test_map_hasUser_noBox_validDomain_tooManyUsers(self):
        d = self.map.get('multiple@example.com')
        self.assertRaises(
            util.ScaleMailAccountMultipleEntries,
            testutil.wait, d)

    def testUgly(self):
        d = self.map.get('""@')
        r = testutil.wait(d)
        self.assertEquals(r, None)
