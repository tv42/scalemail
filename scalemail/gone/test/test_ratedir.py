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

    def tearDown(self):
        if hasattr(self, 'world'):
            self.failIf(self.world.times)
            del self.world

    def test_firstDelivery(self):
        world = FakeWorld(times=[42], id='unique')
        r = ratedir.RateDir(world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        self.failUnless(os.path.isfile(
            os.path.join(self.tmp, 
                         '%s.%u.%s' % (world.uniqueIdentifier(),
                                       42,
                                       'foo@bar'))))

    def test_senderMangling(self):
        world = FakeWorld(times=[42, 42, 42, 42, 42, 42], id='unique')
        r = ratedir.RateDir(world,
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
                             '%s.%u.%s' % (world.uniqueIdentifier(),
                                           42,
                                           mangled))))

    def test_limit_immediate(self):
        world = FakeWorld(times=[42, 42], id='unique')
        r = ratedir.RateDir(world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        self.assertRaises(igone.RateExceededError,
                          r.tick, 'foo@bar')


    def test_limit_oneSecond(self):
        world = FakeWorld(times=[42, 43], id='unique')
        r = ratedir.RateDir(world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        self.assertRaises(igone.RateExceededError,
                          r.tick, 'foo@bar')

    def test_limit_oneHour(self):
        world = FakeWorld(times=[42, 42+1*60*60-1, 42+1*60*60], id='unique')
        r = ratedir.RateDir(world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        self.assertRaises(igone.RateExceededError,
                          r.tick, 'foo@bar')
        self.assertRaises(igone.RateExceededError,
                          r.tick, 'foo@bar')

    def test_limit_overOneHour(self):
        world = FakeWorld(times=[42, 42+1*60*60+1], id='unique')
        r = ratedir.RateDir(world,
                            self.tmp,
                            count=1,
                            interval=1*60*60)
        r.tick('foo@bar')
        r.tick('foo@bar')
