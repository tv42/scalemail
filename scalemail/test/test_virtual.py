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

class AccountGetterDriver(util.AccountGetter):
    def __init__(self, accounts, *a, **kw):
        super(AccountGetterDriver, self).__init__(*a, **kw)
        self.__accounts = accounts

    def _connect(self, domain):
        return defer.succeed(None)

    def _fetch(self,
               proto,
               user, domain,
               ldapAttributeMailbox,
               ldapAttributeMailHost,
               dn):
        accounts = self.__accounts.get((user, domain), [])
        return defer.succeed(accounts)

class VirtualMapFactoryDriver(virtual.ScalemailVirtualMapFactory):
    def __init__(self, accounts={}, *a, **kw):
        virtual.ScalemailVirtualMapFactory.__init__(self, *a, **kw)
        self.__accounts = accounts

    def _getAccount(self, config, local, domain):
        f = AccountGetterDriver(self.__accounts, config)
        return f.getAccount(local, domain)

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
                                                                       'scaleMailAlias': ['bar@example.com',

                                                                                          # do not obey foreign addresses
                                                                                          'thud@something.else.invalid',
                                                                                          ],
                                                                       }),
                                      ],
            ('multiple', 'example.com'):  [1, 2],
            ('one', 'example.com'):  [entry.BaseLDAPEntry(dn='cn=one,dc=example,dc=com',
                                                          attributes={ 'scaleMailHost': ['h1'],
                                                                       'scaleMailAlias': ['numbers@example.com'],
                                                                       }),
                                      ],
            ('two', 'example.com'):  [entry.BaseLDAPEntry(dn='cn=two,dc=example,dc=com',
                                                          attributes={ 'scaleMailHost': ['h1'],
                                                                       'scaleMailAlias': ['numbers@example.com'],
                                                                       }),
                                      ],
            })
                                           
        
    def test_map_domainOnly_notExist(self):
        self.assertEquals(self.map.get('not-exist'),
                          None)

    def test_map_domainOnly_notExist_aliasDomain(self):
        self.assertEquals(self.map.get('something.else.invalid'),
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

    def test_map_domainOnly_hasBox_nonExist_aliasDomain(self):
        # even for non-existing domains
        self.assertEquals(self.map.get('foo.scalemail.something.else.invalid'),
                          None)

    def test_map_hasUser_nonExistingDomain(self):
        self.assertEquals(self.map.get('foo@not-exist'),
                          None)

    def test_map_hasUser_nonExistingDomain_aliasDomain(self):
        self.assertEquals(self.map.get('thud@something.else.invalid'),
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

    def test_map_alias_simple(self):
        d = self.map.get('bar@example.com')
        r = testutil.wait(d)
        self.assertEquals(r, 'foo@example.com')
    test_map_alias_simple.todo = True

    def test_map_alias_multiple(self):
        d = self.map.get('numbers@example.com')
        r = testutil.wait(d)
        self.assertEquals(r, 'one@example.com, two@example.com')
    test_map_alias_multiple.todo = True

    def testUgly(self):
        d = self.map.get('""@')
        r = testutil.wait(d)
        self.assertEquals(r, None)
