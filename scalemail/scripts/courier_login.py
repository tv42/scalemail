import os, sys
from twisted.internet import protocol, reactor
from twisted.mail.maildir import initializeMaildir
from ldaptor import checkers
from ldaptor import config as ldapconfig
from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap import ldaperrors, ldapsyntax, ldapclient, ldapconnector
from scalemail import config
    
class LoginError(Exception):
    pass

class RetryLogin(LoginError):
    pass

class UsageError(RetryLogin):
    pass

class ChainLogin(LoginError):
    pass

class UnknownUser(ChainLogin):
    pass

class BadPassword(ChainLogin):
    pass

class AlreadyAuthenticated(ChainLogin):
    pass

class UnsupportedAuthenticationType(ChainLogin):
    pass

class BadAuthData(ChainLogin):
    pass

class UserIdMustContainAtSign(ChainLogin):
    pass

class BadUserData(ChainLogin):
    pass

### quoting
import re, string
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

def _unbind(entry, client):
    client.unbind()
    return entry

def _fetch(proto, base, mailAttribute, addr, mailhostAttribute):
    baseEntry = ldapsyntax.LDAPEntry(client=proto,
                                     dn=base)
    d=baseEntry.search(filterObject=pureldap.LDAPFilter_equalityMatch(
        attributeDesc=pureldap.LDAPAttributeDescription(value=mailAttribute),
        assertionValue=pureldap.LDAPAssertionValue(value=addr),
        ),
                       attributes=[mailhostAttribute],
                       scope=pureldap.LDAP_SCOPE_wholeSubtree,
                       sizeLimit=1,
                       )
    return d

def bind(config, addr, hostname, password):
    CONFIG_LDAP_ATTRIBUTES_MAIL=config.getLDAPAttributeMailbox()
    CONFIG_LDAP_ATTRIBUTES_MAILHOST=config.getLDAPAttributeMailHost()

    dn = config.getDNForDomain(hostname)
    serviceLocationOverride = config.getServiceLocationOverride()

    c=ldapconnector.LDAPClientCreator(reactor, ldapclient.LDAPClient)
    d=c.connectAnonymously(dn, serviceLocationOverride)
    d.addCallback(_fetch,
                  base=dn,
                  mailAttribute=CONFIG_LDAP_ATTRIBUTES_MAIL,
                  addr=addr,
                  mailhostAttribute=CONFIG_LDAP_ATTRIBUTES_MAILHOST,
                  )

    def cb(results, password):
        if not results:
            raise UnknownUser
        if len(results) > 1:
            raise ManyUsersMatch, addr

        e = results[0]
        # TODO:
        # - make str() unnecessary
        # - allow e.bind(password) -> e?
        d = e.client.bind(str(e.dn), password)
        def _reportError(fail):
            fail.trap(ldaperrors.LDAPInvalidCredentials)
            raise BadPassword
        d.addErrback(_reportError)
        def _cb((matchedDN, serverSaslCreds), e):
            return e
        d.addCallback(_cb, e)
        return d
    d.addCallback(cb, password)
    return d

def getMailhost(config, e):
    CONFIG_LDAP_ATTRIBUTES_MAILHOST=config.getLDAPAttributeMailHost()

    if CONFIG_LDAP_ATTRIBUTES_MAILHOST not in e:
        raise BadUserData, "User %s has no attribute %r" \
            % (e.dn,
               CONFIG_LDAP_ATTRIBUTES_MAILHOST)
    mailhosts = e[CONFIG_LDAP_ATTRIBUTES_MAILHOST]
    if len(mailhosts) != 1:
        raise BadUserData, "User %s has too many mailhosts" % e.dn

    mailhost = mailhosts.pop()
    return mailhost

def main(config, argv, env, service, authtype, authdata):
    if not argv[1:]:
        raise UsageError, "Need to provide some arguments."
    if env.get('AUTHENTICATED'):
        raise AlreadyAuthenticated

    if authtype != 'login':
        raise UnsupportedAuthenticationType, authtype

    l = authdata.splitlines()
    if len(l) == 3 and l[-1] == '':
        # authlib(7) says the empty line shouldn't be there. Nice.
        del l[-1]
    if len(l) != 2:
        raise BadAuthData
    userid, password = l

    userid = userid.replace('%', '@')
    if '@' not in userid:
        raise UserIdMustContainAtSign, userid

    username = userid.split('@', 1)[0]
    hostname = userid.split('@', 1)[1]

    username = quot(username)
    hostname = quot(hostname)

    userpad = (username+'__')[:2]

    d = bind(config, userid, hostname, password)
    d.addCallback(cbLoggedIn, config, env, userid, hostname, userpad, username)
    return d

def cbLoggedIn(e, config, env, userid, hostname, userpad, username):
    mailhost = getMailhost(config, e)

    userdir = os.path.join(config.getSpool(),
                           hostname,
                           mailhost,
                           userpad)

    if not os.path.isdir(userdir):
        os.mkdir(userdir, 0700)

    maildir = os.path.join(userdir, username)

    if not os.path.isdir(maildir):
        initializeMaildir(maildir)

    env['MAILDIR'] = '.'
    env['AUTHENTICATED'] = userid
    return maildir

EX_OK=0
EX_TEMPFAIL=75
EX_USAGE=64
EX_NOUSER=67
EX_NOHOST=68

def die(s):
    print >>sys.stderr, "scalemail-courier-login: %s" % s
    sys.exit(EX_USAGE)

def run():
    import traceback
    from twisted.trial import util

    try:
        cfg = config.ScalemailConfig()
        authfile = os.fdopen(3, 'r')
        service = authfile.readline().rstrip()
        authtype = authfile.readline().rstrip()
        authdata = authfile.read()
        authfile.close()
        try:
            d = main(config=cfg,
                     argv=sys.argv,
                     env=os.environ,
                     service=service,
                     authtype=authtype,
                     authdata=authdata)
            r = util.wait(d)
            os.chdir(r)
            os.execlp(sys.argv[1], *sys.argv[1:])
            die("Something is very wrong")
        except ChainLogin:
            # TODO pass on authinfo
            os.execlp(sys.argv[1], *sys.argv[1:])
            die("Something is very wrong")
        except RetryLogin:
            # TODO pass on authinfo
            l = []

            argc = int(os.environ['AUTHARGC'])
            for i in range(argc):
                l.append(os.environ['AUTHARGV%d' % i])
            os.execlp(*l)
            die("Something is very wrong")
    except SystemExit:
        raise
    except:
        try:
            traceback.print_exc(file=sys.stderr)
        finally:
            sys.exit(EX_TEMPFAIL)
