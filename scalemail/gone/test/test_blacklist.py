import email
from twisted.trial import unittest
from scalemail.gone import blacklist

class Blacklist(unittest.TestCase):
    def check(self, want, sender, s):
        msg = email.message_from_string(s)
        msg.set_unixfrom('From %s' % sender)
        got = blacklist.isBlacklist(msg)
        self.assertEquals(got, want)

    def ok(self, sender, msg):
        self.check(False, sender, msg)

    def test_simple(self):
        self.ok('foo@bar', '''\
From: thud@quux
Subject: foo
''')

    def test_bounce(self):
        self.check('Sender is empty, mail came from system account',
                   '', '''\
From: thud@quux
Subject: bounce
''')

    # TODO write more tests
