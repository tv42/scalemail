import sys, sets
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEMessage import MIMEMessage
from twisted.internet import defer
from twisted.protocols import smtp
from scalemail.gone import igone, blacklist, ratedir, util

def _process(path, msg):
    """
    @todo: rate, interval configuration
    """
    world = util.RealWorld()

    err = blacklist.isBlacklist(msg)
    if err:
        return err

    seen = sets.Set()
    for deliveredTo in msg.get_all('Delivered-To', []):
        if deliveredTo in seen:
            # duplicate Delivered-To -- loop detected
            return "Message has duplicated Delivered-To line: %s" % deliveredTo
        seen.add(deliveredTo)

    rate = ratedir.RateDir(world, path)
    sender = util.getSender(msg)
    try:
        rate.tick(sender)
    except igone.RateExceededError, e:
        return "Sender has sent too many messages"

    reply = MIMEMultipart()
    reply['To'] = sender

    subjectPrefix = None # TODO make configurable
    subject = msg['Subject']
    if subject is None:
        subject = 'Your mail'
    if subjectPrefix is not None:
        subject = subjectPrefix + subject
    reply['Subject'] = subject

    msgid = msg.get('Message-ID', None)
    if msgid is not None:
        msgid = msgid.strip()
        reply['In-Reply-To'] = msgid

    reply.attach(MIMEText('foo'.encode('utf-8'), _charset='utf-8'))
    reply.attach(MIMEMessage(msg))
    
    d = smtp.sendmail('127.0.0.1',
                      'TODO-set-from-here',
                      [sender],
                      reply)
    d.addCallback(lambda _ : False)
    #TODO handle sendmail status
    return d


def process(path, msg):
    """
    @return: An object that is true if message was not autoreplied
    to. Otherwise, it is non-true. If it is true, it can be
    stringified for an explanation.

    @rtype: Deferred
    """
    return defer.maybeDeferred(_process, path, msg)
