from twisted.trial import unittest
import email
from scalemail.gone import respond, util

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
