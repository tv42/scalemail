import os
from twisted.trial import unittest
from twisted.internet import defer
from twisted.cred import error
from cStringIO import StringIO
from ldaptor import config as ldapconfig
from scalemail.scripts import courier_login
from scalemail.test.test_virtual import SetupMixin
from ldaptor.test import util as ldaptestutil

class Login(SetupMixin, unittest.TestCase):
    ldif = """version: 1
dn: dc=example,dc=com

dn: cn=fred,dc=example,dc=com
objectClass: bork
mail: fred@example.com
scaleMailHost: h1

"""
    def setUp(self):
        SetupMixin.setUp(self)
        d=self.config.db.lookup('cn=fred,dc=example,dc=com')
        ldapconfig.loadConfig(configFiles=[], reload=True)
        def _setPassword(e, password):
            return e.setPassword(password)
        d.addCallback(_setPassword, 'flintstone')
        ldaptestutil.pumpingDeferredResult(d)
        os.mkdir(os.path.join(self.spool, 'example.com', 'h1'))

    def test_noArgs(self):
        d = defer.maybeDeferred(courier_login.main,
                                config=self.config,
                                argv=['you'],
                                env={},
                                service='fake',
                                authtype='fake',
                                authdata='fake')
        fail = ldaptestutil.pumpingDeferredError(d)
        fail.trap(courier_login.UsageError)

    def test_authenticated(self):
        d = defer.maybeDeferred(courier_login.main,
                                config=self.config,
                                argv=['you', 'someone-else', 'foo'],
                                env={
            'AUTHENTICATED': 'someone',
           },
                                service='fake',
                                authtype='fake',
                                authdata='fake')
        fail = ldaptestutil.pumpingDeferredError(d)
        fail.trap(courier_login.AlreadyAuthenticated)

    def test_bad_authtype(self):
        env = {}
        d = defer.maybeDeferred(courier_login.main,
                                config=self.config,
                                argv=['you', 'someone-else', 'foo'],
                                env=env,
                                service='fakeserv',
                                authtype='bad',
                                authdata='fake')
        fail = ldaptestutil.pumpingDeferredError(d)
        fail.trap(courier_login.UnsupportedAuthenticationType)

    def test_plain_username(self):
        env = {}
        d = defer.maybeDeferred(courier_login.main,
                                config=self.config,
                                argv=['you', 'someone-else', 'foo'],
                                env=env,
                                service='fakeserv',
                                authtype='login',
                                authdata='fred\nflintstone')
        fail = ldaptestutil.pumpingDeferredError(d)
        fail.trap(courier_login.UserIdMustContainAtSign)

    def test_wrong_password(self):
        env = {}
        d = defer.maybeDeferred(courier_login.main,
                                config=self.config,
                                argv=['you', 'someone-else', 'foo'],
                                env=env,
                                service='fakeserv',
                                authtype='login',
                                authdata='fred@example.com\nrubbles')
        fail = ldaptestutil.pumpingDeferredError(d)
        fail.trap(error.UnauthorizedLogin)

    def test_success(self):
        env = {}
        d = defer.maybeDeferred(courier_login.main,
                                config=self.config,
                                argv=['you', 'someone-else', 'foo'],
                                env=env,
                                service='fakeserv',
                                authtype='login',
                                authdata='fred@example.com\nflintstone')
        r = ldaptestutil.pumpingDeferredResult(d)
        self.assertEquals(r, os.path.join(self.spool,
                                          'example.com',
                                          'h1',
                                          'fr',
                                          'fred'))
        self.assertEquals(env.get('AUTHENTICATED'),
                          'fred@example.com')
        self.assertEquals(env.get('MAILDIR'), '.')
