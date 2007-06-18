from twisted.trial import unittest
from twisted.internet import defer, protocol
import os
from scalemail import config, util
from ldaptor.protocols.ldap import distinguishedname, ldapclient, ldaperrors, ldapserver
from ldaptor.protocols import pureldap

class ConfigDriver(config.ScalemailConfig):
    configFiles = []
    def __init__(self, spool, overrides):
        config.ScalemailConfig.__init__(self)
        self.config.set('Scalemail', 'spool', spool)
        self.__overrides = overrides
    def getServiceLocationOverride(self):
        result = config.ScalemailConfig.getServiceLocationOverride(self)

        for dn,dest in self.__overrides.items():
            if not isinstance(dn, distinguishedname.DistinguishedName):
                dn = distinguishedname.DistinguishedName(stringValue=dn)
            assert dn not in result
            result[dn]=dest
        return result

def _overrideConnect(factory):
    class LDAPServerThatFailsSearches(ldapserver.LDAPServer):
        def handle_LDAPSearchRequest(self, request, controls, reply):
            return defer.succeed(
                pureldap.LDAPSearchResultDone(resultCode=ldaperrors.LDAPOther.resultCode,
                                              errorMessage='just testing'))

    class FakeTransport:
        def __init__(self, target):
            self.target = target
        def write(self, data):
            self.target.dataReceived(data)
        def writeSequence(self, data):
            self.write(''.join(data))
        def loseConnection(self):
            self.target.connectionLost(protocol.connectionDone)

    client = factory.buildProtocol(None)
    server = LDAPServerThatFailsSearches()

    c2s = FakeTransport(server)
    c2s.protocol = client
    client.makeConnection(c2s)

    s2c = FakeTransport(client)
    s2c.protocol = server
    server.makeConnection(s2c)

def raises(exception, f, *args, **kwargs):
    """Determine whether the given call raises the given exception"""
    try:
        f(*args, **kwargs)
    except exception, e:
        return e
    return None

class CountingLDAPClient(ldapclient.LDAPClient):
    count = 0

    def connectionMade(self):
        self.__class__.count += 1
        ldapclient.LDAPClient.connectionMade(self)

    def connectionLost(self, reason):
        ldapclient.LDAPClient.connectionLost(self, reason)
        self.__class__.count -= 1

class TestGetAccount(unittest.TestCase):
    def setUp(self):
        self.spool = self.mktemp()
        os.mkdir(self.spool)
        os.mkdir(os.path.join(self.spool, 'example.com'))
        self.config = ConfigDriver(spool=self.spool,
                                   overrides={
            'dc=': _overrideConnect,
            })

    def testFDLeakBug(self):
        d = util.getAccount(self.config,
                            local='""',
                            domain='',
                            clientFactory=CountingLDAPClient)
        self.assertFailure(d, ldaperrors.LDAPOther)
        def cb(e):
            self.assertEquals(e.message, 'just testing')
            self.assertEquals(CountingLDAPClient.count, 0)
        d.addCallback(cb)
        return d
