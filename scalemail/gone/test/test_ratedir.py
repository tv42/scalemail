import os
from zope.interface import implements
from twisted.trial import unittest
from scalemail.gone import igone, ratedir

class FakeWorld(object):
    implements(igone.IRealWorld)

    def __init__(self, times, id):
        self.times = times
        self.id = id

    def currentTime(self):
        time = self.times.pop(0)
        return time

    def uniqueIdentifier(self):
        return self.id
        

class Test(unittest.TestCase):
    def setUp(self):
        self.tmp = self.mktemp()
        os.mkdir(self.tmp)

    def makeWorld(self, times):
        assert not hasattr(self, 'world')
        self.world = FakeWorld(times=times, id='unique')

    def tearDown(self):
        if hasattr(self, 'world'):
            self.failIf(self.world.times)
            del self.world

    def test_firstDelivery(self):
        self.makeWorld(times=[42])
        r = ratedir.RateDir(self.world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        self.failUnless(os.path.isfile(
            os.path.join(self.tmp, 
                         '%s.%u.%s' % (self.world.uniqueIdentifier(),
                                       42,
                                       'foo@bar'))))

    def test_senderMangling(self):
        self.makeWorld(times=[42, 42, 42, 42, 42, 42])
        r = ratedir.RateDir(self.world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        SENDERS = [
            ('/foo@bar', ':foo@bar'),
            ('fo/o@bar', 'fo:o@bar'),
            ('foo/@bar', 'foo:@bar'),
            ('foo@/bar', 'foo@:bar'),
            ('foo@b/ar', 'foo@b:ar'),
            ('foo@bar/', 'foo@bar:'),
            ]
        
        for orig, mangled in SENDERS:
            r.tick(orig)
        for orig, mangled in SENDERS:
            self.failUnless(os.path.isfile(
                os.path.join(self.tmp, 
                             '%s.%u.%s' % (self.world.uniqueIdentifier(),
                                           42,
                                           mangled))))

    def test_limit_immediate(self):
        self.makeWorld(times=[42, 42])
        r = ratedir.RateDir(self.world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        self.assertRaises(igone.RateExceededError,
                          r.tick, 'foo@bar')


    def test_limit_oneSecond(self):
        self.makeWorld(times=[42, 43])
        r = ratedir.RateDir(self.world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        self.assertRaises(igone.RateExceededError,
                          r.tick, 'foo@bar')

    def test_limit_oneHour(self):
        self.makeWorld(times=[42, 42+1*60*60-1, 42+1*60*60])
        r = ratedir.RateDir(self.world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        self.assertRaises(igone.RateExceededError,
                          r.tick, 'foo@bar')
        self.assertRaises(igone.RateExceededError,
                          r.tick, 'foo@bar')

    def test_limit_overOneHour(self):
        self.makeWorld(times=[42, 42+1*60*60+1])
        r = ratedir.RateDir(self.world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        r.tick('foo@bar')

    def test_linkFail(self):
        self.makeWorld(times=[42])
        r = ratedir.RateDir(self.world,
                            self.tmp,
                            count=1,
                            interval=10)
        # make the hard linking fail by providing a directory as a
        # link target
        os.mkdir(os.path.join(self.tmp,
                              '%s.%u.%s' % (self.world.uniqueIdentifier(),
                                            42,
                                            'someoneelse@bar')))
        r.tick('foo@bar')
        self.failUnless(os.path.isfile(
            os.path.join(self.tmp, 
                         '%s.%u.%s' % (self.world.uniqueIdentifier(),
                                       42,
                                       'foo@bar'))))

    def test_ignoreJunk(self):
        self.makeWorld(times=[42])
        r = ratedir.RateDir(self.world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        FILES = [
            '.foo',
            'a.b',
            'a.2.b.c',
            'a.2.b.c.d',
            'a.nonnumeric.c',
            ]
        for filename in FILES:
            file(os.path.join(self.tmp, filename), 'w').close()
        r.tick('foo@bar')
        for filename in FILES:
            self.failUnless(os.path.isfile(os.path.join(self.tmp, filename)))

    def test_ignoreRemoveError(self):
        self.makeWorld(times=[1, 5*60*60])
        r = ratedir.RateDir(self.world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        r.tick('foo@bar')
