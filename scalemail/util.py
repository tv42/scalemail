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

def addr_join(user, folder, host, recipientDelimiter):
    """
    Join user, folder and host to an email address.

    @param folder: folder name or None for no folder.

    @param recipientDelimiter: string of recipient delimiter
    characters, only the first one will be used.
    """
    local = user
    if folder is not None:
        local = (local
                 + recipientDelimiter[0]
                 + folder)
    return local+'@'+host

class ScaleMailAccountSearchError(Exception):
    """An error occurred during LDAP search for the account."""

    def __str__(self):
        return self.__doc__

class ScaleMailAccountNotFound(ScaleMailAccountSearchError):
    """User not found in LDAP"""

class ScaleMailAccountMultipleEntries(ScaleMailAccountSearchError):
    """User matches multiple LDAP entries, LDAP content inconsistent"""

class AccountGetter(object):
    clientFactory = ldapclient.LDAPClient

    def __init__(self,
                 config,
                 local, domain,
                 clientFactory=None,
                 *a, **kw):
        super(AccountGetter, self).__init__(*a, **kw)
        self.config = config
        if clientFactory is not None:
            self.clientFactory = clientFactory
        self.domain = domain
        self.user, self.folder = addr_split(local, self.config.getRecipientDelimiters())

    def _connect(self):
        dn = self.config.getDNForDomain(self.domain)
        c = ldapconnector.LDAPClientCreator(reactor, self.clientFactory)
        d = c.connectAnonymously(dn, self.config.getServiceLocationOverride())
        return d

    def _fetch(self, proto):
        dn = self.config.getDNForDomain(self.domain)
        o = ldapsyntax.LDAPEntry(client=proto, dn=dn)
        ldapAttributeMailbox=self.config.getLDAPAttributeMailbox()
        d=o.search(filterObject=pureldap.LDAPFilter_equalityMatch(
            attributeDesc=pureldap.LDAPAttributeDescription(ldapAttributeMailbox),
            assertionValue=pureldap.LDAPAssertionValue(self.user+'@'+self.domain)))

        d.addBoth(self._unbind, proto)
        return d

    def _unbind(self, r, proto):
        proto.unbind()
        return r

    def _searchCompleted(self, entries):
        if len(entries) < 1:
            raise ScaleMailAccountNotFound
        if len(entries) > 1:
            raise ScaleMailAccountMultipleEntries
        e = entries[0]
        return e

    def getAccount(self):
        """
        Get the LDAPEntry for this account.
        """
        d = self._connect()
        d.addCallback(self._fetch)
        d.addCallback(self._searchCompleted)
        return d

def getAccount(config, local, domain,
               clientFactory=None):
    f = AccountGetter(config, local, domain,
                      clientFactory=clientFactory)
    return f.getAccount()

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
