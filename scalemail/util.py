from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap import ldapclient, ldapsyntax, ldapconnector
from twisted.internet import reactor
import string, random

### quoting
import re
_quot_trans = string.maketrans('', '')
_quot_trans = string.lower(_quot_trans)
_quot_trans = re.sub("[^a-z0-9.-]", '_', _quot_trans)

_quot_re = re.compile(r'\.+')

def quot(s):
    match = _quot_re.match(s)
    if match:
        s = match.end()*'_' + s[match.end():]
    s=string.translate(s, _quot_trans)
    return s


def host_split(host):
    """Split host part of email address into box and domain"""
    separator=".scalemail."
    i=host.find(separator)
    if i==-1:
        if host.startswith('scalemail.'):
            return (None, host[len('scalemail.'):])
        else:
            return (None, None)
    box=quot(host[:i])
    domain=quot(host[i+len(separator):])
    return (box, domain)

def addr_split(addr, recipientDelimiters):
    """Split local part of email address into user and folder"""
    user=quot(addr)
    folder=None
    for c in recipientDelimiters:
        try:
            i=string.index(addr, c)
        except ValueError:
            pass
        else:
            user=quot(addr[:i])
            folder=quot(addr[i+1:])
            break
    return (user, folder)

class ScaleMailAccountSearchError(Exception):
    """An error occurred during LDAP search for the account."""

    def __str__(self):
        return self.__doc__

class ScaleMailAccountNotFound(ScaleMailAccountSearchError):
    """User not found in LDAP"""

class ScaleMailAccountMultipleEntries(ScaleMailAccountSearchError):
    """User matches multiple LDAP entries, LDAP content inconsistent"""

def getAccount(config, local, domain):
    """

    Get the LDAPEntry for this account.

    """
    username, folder = addr_split(local, config.getRecipientDelimiters())

    dn = config.getDNForDomain(domain)
    c = ldapconnector.LDAPClientCreator(reactor, ldapclient.LDAPClient)
    d = c.connect(dn, config.getServiceLocationOverride())

    def _bind(proto):
        d=proto.bind()
        d.addCallback(lambda _: proto)
        return d

    d.addCallback(_bind)

    def _fetch(proto,
               user, domain,
               ldapAttributeMailbox,
               ldapAttributeMailHost,
               dn):
        o = ldapsyntax.LDAPEntry(client=proto, dn=dn)
        d=o.search(filterObject=pureldap.LDAPFilter_equalityMatch(
            attributeDesc=pureldap.LDAPAttributeDescription(ldapAttributeMailbox),
            assertionValue=pureldap.LDAPAssertionValue(user+'@'+domain)))

        def _unbind(entries, proto):
            proto.unbind()
            return entries
        d.addCallback(_unbind, proto)

        return d

    d.addCallback(_fetch,
                  user=username, domain=domain,
                  ldapAttributeMailbox=config.getLDAPAttributeMailbox(),
                  ldapAttributeMailHost=config.getLDAPAttributeMailHost(),
                  dn=config.getDNForDomain(domain))

    def _searchCompleted(entries):
        if len(entries) < 1:
            raise ScaleMailAccountNotFound
        if len(entries) > 1:
            raise ScaleMailAccountMultipleEntries
        e = entries[0]
        return e

    d.addCallback(_searchCompleted)

    return d

def getBoxes(entry, config):
    """

    Get the backend boxes that serve this user.

    """

    ldapAttributeMailHost = config.getLDAPAttributeMailHost()
    boxes = entry.get(ldapAttributeMailHost, [])
    return boxes

def getRandomBox(entry, config):
    boxes = getBoxes(entry, config)
    if not boxes:
        return None
    else:
        return random.choice(list(boxes))
