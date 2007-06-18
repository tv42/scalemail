from twisted.trial import unittest
import email
from scalemail.gone import respond

class Prepare(unittest.TestCase):
    def setUp(self):
        self.msg = email.message_from_string("""\
From the-sender
To: the-guy-on-vacation
Subject: question

are you there?
""")

    def test_subject_preserve(self):
        reply = email.message_from_string("""\
Subject: precious

body
""")
        r = respond.prepare(self.msg,
                            reply,
                            subjectPrefix=None)
        self.assertEquals(r.get_all('Subject'), ['precious'])

    def test_subject_preserve_prefix(self):
        reply = email.message_from_string("""\
Subject: precious

body
""")
        r = respond.prepare(self.msg,
                            reply,
                            subjectPrefix='On holiday')
        self.assertEquals(r.get_all('Subject'), ['precious'])

    def test_subject_set(self):
        reply = email.message_from_string("""\

body
""")
        r = respond.prepare(self.msg,
                            reply,
                            subjectPrefix=None)
        self.assertEquals(r.get_all('Subject'), ['question'])

    def test_subject_set_prefix(self):
        reply = email.message_from_string("""\

body
""")
        r = respond.prepare(self.msg,
                            reply,
                            subjectPrefix='On holiday: ')
        self.assertEquals(r.get_all('Subject'), ['On holiday: question'])

    def test_subject_set_noIncoming(self):
        reply = email.message_from_string("""\

body
""")
        msg = email.message_from_string("""\
From the-sender
To: the-guy-on-vacation

are you there?
""")
        r = respond.prepare(msg,
                            reply,
                            subjectPrefix=None)
        self.assertEquals(r.get_all('Subject'), ['Your mail'])

    def test_subject_set_prefix_noIncoming(self):
        reply = email.message_from_string("""\

body
""")
        msg = email.message_from_string("""\
From the-sender
To: the-guy-on-vacation

are you there?
""")
        r = respond.prepare(msg,
                            reply,
                            subjectPrefix='On holiday: ')
        self.assertEquals(r.get_all('Subject'), ['On holiday: Your mail'])

    def test_from_preserve(self):
        """If gone message has From:, that is used."""
        reply = email.message_from_string("""\
From: me

body
""")
        r = respond.prepare(self.msg, reply)
        self.assertEquals(r.get_all('From'), ['me'])

    def test_from_recipient(self):
        """If gone message has no From:, envelope recipient is used."""
        reply = email.message_from_string("""\
Subject: precious

body
""")
        msg = email.message_from_string("""\
From the-sender
Subject: question

are you there?
""")
        r = respond.prepare(msg, reply, recipient='the-recipient')
        self.assertEquals(r.get_all('From'), ['the-recipient'])

    def test_from_recipient_scalemail(self):
        """Even if recipient has scalemail box in its domain, From header doesn't."""
        reply = email.message_from_string("""\
Subject: precious

body
""")
        msg = email.message_from_string("""\
From the-sender
Subject: question

are you there?
""")
        r = respond.prepare(msg, reply, recipient='the-recipient@somehost.scalemail.foo.example.com')
        self.assertEquals(r.get_all('From'), ['the-recipient@foo.example.com'])

    def test_from_recipient_withName(self):
        """If recipient name is given, it is used in From:."""
        reply = email.message_from_string("""\
Subject: precious

body
""")
        msg = email.message_from_string("""\
From the-sender
Subject: question

are you there?
""")
        r = respond.prepare(msg, reply,
                            recipient='the-recipient',
                            recipientName='Jack Recipient',
                            )
        self.assertEquals(r.get_all('From'), ['Jack Recipient <the-recipient>'])

    def test_to_From(self):
        """Original From: is used as To: when available."""
        reply = email.message_from_string("""\
Subject: precious

body
""")
        msg = email.message_from_string("""\
From the-sender
Subject: question
From: Test Person <test@example.com>

are you there?
""")
        r = respond.prepare(msg, reply, recipient='the-recipient')
        self.assertEquals(r.get_all('To'), ['Test Person <test@example.com>'])

    def test_to_Sender(self):
        """Original Sender: overrides From: as response To:."""
        reply = email.message_from_string("""\
Subject: precious

body
""")
        msg = email.message_from_string("""\
From the-sender
Subject: question
From: Test Person <test@example.com>
Sender: RFC2822 sender info <bar@example.com>

are you there?
""")
        r = respond.prepare(msg, reply, recipient='the-recipient')
        self.assertEquals(r.get_all('To'), ['RFC2822 sender info <bar@example.com>'])

    def test_to_From_commas(self):
        """Commas in From do not confuse respond (note invalid input, missing Sender)"""
        reply = email.message_from_string("""\
Subject: precious

body
""")
        msg = email.message_from_string("""\
From the-sender
Subject: question
From: Test Person <test@example.com>, Foo Bar <foo@example.com>

are you there?
""")
        r = respond.prepare(msg, reply, recipient='the-recipient')
        self.assertEquals(r.get_all('To'), ['Test Person <test@example.com>, Foo Bar <foo@example.com>'])

    def test_to_From_multiple(self):
        """Commas in From do not confuse respond (note invalid input, missing Sender)"""
        reply = email.message_from_string("""\
Subject: precious

body
""")
        msg = email.message_from_string("""\
From the-sender
Subject: question
From: Test Person <test@example.com>
From: Foo Bar <foo@example.com>

are you there?
""")
        r = respond.prepare(msg, reply, recipient='the-recipient')
        self.assertEquals(r.get_all('To'), ['Test Person <test@example.com>',
                                            'Foo Bar <foo@example.com>'])

    def test_to_envelopeSender(self):
        """Envelope sender is used as To: when original has no From:."""
        reply = email.message_from_string("""\
Subject: precious

body
""")
        r = respond.prepare(self.msg, reply, recipient='the-recipient')
        self.assertEquals(r.get_all('To'), ['the-sender'])

    def test_order(self):
        """Headers are added in human-friendly order, From/To/Subject."""
        reply = email.message_from_string("""\

body
""")
        r = respond.prepare(self.msg, reply, recipient='the-recipient')
        self.assertEquals(r.keys(), ['From', 'To', 'Subject'])
