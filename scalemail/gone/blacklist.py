from scalemail.gone import util

def isBadSender(sender):
    """
    Was the message sent by a sender to whom one should never respond?

    @param sender: Envelope sender.
    @type sender: string

    @return: An object that is true if message came from a blacklisted
    sender. Otherwise, it is non-true. If it is true, it can be
    stringified for an explanation.
    """
    if sender == '':
        return "Sender is empty, mail came from system account"
    if sender == "#@[]":
        return "Sender is <#@[]> (double bounce message)"
    if '@' not in sender:
        return "Sender did not contain a hostname"
    if sender.lower().startswith('mailer-daemon@'):
        return "Sender was mailer-daemon"
    return False

def isMailingList(msg):
    """
    Was the message sent by a mailing list?

    @param msg: the message
    @type msg: email.Message

    @return: An object that is true if message came from a mailing
    list. Otherwise, it is non-true. If it is true, it can be
    stringified for an explanation.
    """
    MLHEADERS = [
        "List-ID",
        "Mailing-List",
        "X-Mailing-List",
        "X-ML-Name",
        "List-Help",
        "List-Unsubscribe",
        "List-Subscribe",
        "List-Post",
        "List-Owner",
        "List-Archive",
        ]
    for header in MLHEADERS:
        if header in msg:
            return "Message appears to be from a mailing list (%s header)" % header
    return False

def isBlacklist(msg):
    """
    Should we never autorespond to this message?

    @param msg: the message
    @type msg: email.Message

    @return: An object that is true if message was
    blacklisted. Otherwise, it is non-true. If it is true, it can be
    stringified for an explanation.
    """
    sender = util.getSender(msg)
    r = isBadSender(sender)
    if r:
        return r

    r = isMailingList(msg)
    if r:
        return r

    for s in msg.get_all('Precedence', []):
        precedence = s.split(None, 1)[0]
        if precedence.lower() in ['junk', 'bulk', 'list']:
            return "Message has a junk, bulk, or list precedence header"

    return False
