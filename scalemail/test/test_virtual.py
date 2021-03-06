from twisted.trial import unittest
from twisted.internet import defer, protocol, address
from twisted.python import components
import os
from cStringIO import StringIO
from scalemail import virtual, config, util
from ldaptor import inmemory, interfaces
from ldaptor.protocols.ldap import ldapclient, ldapserver
from ldaptor.test import util as ldaptestutil

class ConfigDriver(config.ScalemailConfig):
    configFiles = []
    def __init__(self, spool, ldif):
        config.ScalemailConfig.__init__(self)
        self.config.set('Scalemail', 'spool', spool)

        d = inmemory.fromLDIFFile(StringIO(ldif))
        assert d.called, 'The Deferred must trigger synchronously'
        self.db = d.result

    def getServiceLocationOverride(self):
        return {'': self._createClient}

    def _createClient(self, factory):
        class LDAPServerFactory(protocol.ServerFactory):
            protocol = ldapserver.LDAPServer
            def __init__(self, root):
                self.root = root

        components.registerAdapter(lambda x: x.root,
                                   LDAPServerFactory,
                                   interfaces.IConnectedLDAPEntry)
        serverFactory = LDAPServerFactory(self.db)

        client = ldapclient.LDAPClient()
        server = serverFactory.buildProtocol(address.IPv4Address('TCP', 'localhost', '1024'))
        ldaptestutil.returnConnected(server, client)

        factory.deferred.callback(client)


class SetupMixin:
    def setUp(self):
        self.spool = self.mktemp()
        os.mkdir(self.spool)
        os.mkdir(os.path.join(self.spool, 'example.com'))
        self.config = ConfigDriver(spool=self.spool,
                                   ldif=self.ldif)
        self.map = virtual.ScalemailVirtualMapFactory(self.config)
        


class TestVirtual(SetupMixin, unittest.TestCase):
    ldif = """version: 1
dn: dc=example,dc=com

dn: cn=foo,dc=example,dc=com
mail: foo@example.com
scaleMailHost: h1
scaleMailAlias: anotherfoo@example.com
# do not obey foreign addresses
scaleMailAlias: thud@something.else.invalid

dn: cn=duplicate1,dc=example,dc=com
mail: multiple@example.com
scaleMailHost: h1

dn: cn=duplicate2,dc=example,dc=com
mail: multiple@example.com
scaleMailHost: h1

dn: cn=one,dc=example,dc=com
mail: one@example.com
scaleMailHost: h1
scaleMailAlias: numbers@example.com

dn: cn=two,dc=example,dc=com
mail: two@example.com
scaleMailHost: h1
scaleMailAlias: numbers@example.com

"""

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
        r = ldaptestutil.pumpingDeferredResult(d)
        self.assertEquals(r, 'foo@h1.scalemail.example.com')

    def test_map_hasUser_noBox_validDomain_noUser(self):
        d = self.map.get('bar@example.com')
        r = ldaptestutil.pumpingDeferredResult(d)
        self.assertEquals(r, None)

    def test_map_hasUser_noBox_validDomain_tooManyUsers(self):
        d = self.map.get('multiple@example.com')
        self.assertRaises(
            util.ScaleMailAccountMultipleEntries,
            ldaptestutil.pumpingDeferredResult, d)

    def test_map_alias_simple(self):
        d = self.map.get('anotherfoo@example.com')
        r = ldaptestutil.pumpingDeferredResult(d)
        self.assertEquals(r, 'foo@example.com')

    def test_map_alias_multiple(self):
        d = self.map.get('numbers@example.com')
        r = ldaptestutil.pumpingDeferredResult(d)
        got = r.split(', ')
        got.sort()
        wanted = ['one@example.com', 'two@example.com']
        wanted.sort()
        self.assertEquals(got, wanted)

    def testUgly(self):
        d = defer.execute(self.map.get, '""@')
        r = ldaptestutil.pumpingDeferredResult(d)
        self.failUnlessIdentical(r, None)

    def testUgly_has_local(self):
        d = defer.execute(self.map.get, 'foo@')
        r = ldaptestutil.pumpingDeferredResult(d)
        self.failUnlessIdentical(r, None)

    def test_extension_simple(self):
        d = self.map.get('foo+some.extension.here@example.com')
        r = ldaptestutil.pumpingDeferredResult(d)
        self.assertEquals(r, 'foo+some.extension.here@h1.scalemail.example.com')

    def test_extension_alias(self):
        d = self.map.get('anotherfoo+some.extension.here@example.com')
        r = ldaptestutil.pumpingDeferredResult(d)
        self.assertEquals(r, 'foo+some.extension.here@example.com')

class Alias(SetupMixin, unittest.TestCase):
    ldif = """version: 1
dn: dc=example,dc=com

dn: cn=real,dc=example,dc=com
mail: foo@example.com
scaleMailHost: h1

dn: cn=fake,dc=example,dc=com
mail: somethingelse@example.com
scaleMailHost: h1
scaleMailAlias: foo@example.com

"""

    def test_conflict(self):
        d = self.map.get('foo@example.com')
        self.assertRaises(
            util.ScaleMailAccountMultipleEntries,
            ldaptestutil.pumpingDeferredResult, d)
