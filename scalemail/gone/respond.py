import sets
from email.MIMEMultipart import MIMEMultipart
from email.MIMEMessage import MIMEMessage
from twisted.internet import defer
from twisted.protocols import smtp
from scalemail.gone import igone, blacklist, ratedir, util

def _shouldProcess(path, msg):
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
    except igone.RateExceededError:
        return "Sender has sent too many messages"

    return False

def _prepare(msg,
             reply,
             subjectPrefix=None):
    sender = util.getSender(msg)
    reply['To'] = sender

    if 'Subject' not in reply:
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

    if reply.is_multipart():
        reply.attach(MIMEMessage(msg))
    return reply
    
def _send(msg, smtpHost, sender, recipient):
    d = smtp.sendmail(smtpHost,
                      sender,
                      [recipient],
                      msg)
    d.addCallback(lambda _ : False)
    return d

def _process(path,
             msg,
             sender,
             goneInfo,
             smtpHost=None,
             ):
    if smtpHost is None:
        smtpHost = '127.0.0.1'
    d = defer.maybeDeferred(_shouldProcess, path, msg)
    def _cb(r, msg):
        if r:
            return r
        d = defer.maybeDeferred(_prepare, msg,
                                reply=goneInfo.message,
                                subjectPrefix=goneInfo.settings.get('Subject', None))
        d.addCallback(_send,
                      smtpHost=smtpHost,
                      sender=sender,
                      recipient=util.getSender(msg))
        return d
    d.addCallback(_cb, msg)
    return d

def process(*a, **kw):
    """
    @return: An object that is true if message was not autoreplied
    to. Otherwise, it is non-true. If it is true, it can be
    stringified for an explanation.

    @rtype: Deferred
    """
    return defer.maybeDeferred(_process, *a, **kw)
