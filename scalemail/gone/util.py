import os, time
from zope.interface import implements
from scalemail.gone import igone

def getSender(msg):
    from_ = msg.get_unixfrom()
    assert from_.startswith('From ')
    return from_[len('From '):]

class RealWorld(object):
    implements(igone.IRealWorld)
    counter = 0

    def __init__(self):
        self.__class__.counter += 1
        self.counter = self.__class__.counter

    def currentTime(self):
        return time.time()

    def uniqueIdentifier(self):
        return '%u_%u' % (os.getpid(), self.counter)
