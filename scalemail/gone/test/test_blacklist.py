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

    def test_doublebounce(self):
        self.check('Sender is <#@[]> (double bounce message)',
                   '#@[]', '''\
From: thud@quux
Subject: bounce
''')

    def test_localonly(self):
        self.check('Sender did not contain a hostname',
                   'foo', '''\
From: thud@quux
Subject: bounce
''')

    def test_mailerDaemon(self):
        self.check('Sender was mailer-daemon',
                   'mailer-daemon@foo', '''\
From: thud@quux
Subject: bounce
''')
        self.check('Sender was mailer-daemon',
                   'mailer-DAEMON@foo', '''\
From: thud@quux
Subject: bounce
''')
        self.ok('mailer-DAEMONs-best-buddy@something', '''\
From: thud@quux
Subject: pass
''')

    def test_mailingList(self):
        self.check('Message appears to be from a mailing list (List-ID header)',
                   'foo@bar', '''\
From: thud@quux
LIST-id: foo
Subject: bounce
''')

    def test_precedence_bulk(self):
        self.check('Message has a junk, bulk, or list precedence header',
                   'foo@bar', '''\
From: thud@quux
Precedence: bulk or something
Subject: bounce
''')
