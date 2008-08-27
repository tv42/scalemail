import sets
from email.MIMEMessage import MIMEMessage
import email.Utils
from twisted.internet import defer
from twisted.mail import smtp
from scalemail.gone import igone, blacklist, ratedir
from scalemail.gone import util as goneutil
from scalemail import util

def _shouldProcess(path, msg):
    """
    @todo: rate, interval configuration
    """
    world = goneutil.RealWorld()

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
    sender = goneutil.getSender(msg)
    try:
        rate.tick(sender)
    except igone.RateExceededError:
        return "Sender has sent too many messages"

    return False

def prepare(msg,
            reply,
            recipient=None,
            recipientName=None,
            subjectPrefix=None):
    sender = goneutil.getSender(msg)

    if ('From' not in reply
        and recipient is not None):
            if '@' in recipient:
                local, host = recipient.split('@', 1)
                box, domain = util.host_split(host)
                if domain is not None:
                    host = domain
                recipient = str(smtp.Address(local, host))
            reply['From'] = email.Utils.formataddr((recipientName, recipient))

    to = msg.get_all('Sender', None)
    if to is None:
        to = msg.get_all('From', None)
    if to is None:
        to = [sender]
    for addr in to:
        reply['To'] = addr

    if 'Subject' not in reply:
        subject = msg['Subject']
        if subject is None:
            # echo foo | mail testaccount has no subject, if vacation
            # message has no subject either, sees this.. ugly due to
            # lack of l10n
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
             recipient,
             recipientName=None,
             smtpHost=None,
             ):
    if smtpHost is None:
        smtpHost = '127.0.0.1'
    d = defer.maybeDeferred(_shouldProcess, path, msg)
    def _cb(r, msg):
        if r:
            return r
        d = defer.maybeDeferred(prepare, msg,
                                reply=goneInfo.message,
                                recipient=recipient,
                                recipientName=recipientName,
                                subjectPrefix=goneInfo.settings.get('Subject', None))
        d.addCallback(_send,
                      smtpHost=smtpHost,
                      sender=sender,
                      recipient=goneutil.getSender(msg))
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
