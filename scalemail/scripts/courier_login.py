import os, sys, pwd, grp
from twisted.internet import protocol, reactor, defer
from twisted.cred import credentials, error
from twisted.mail.maildir import initializeMaildir
from twisted.python.util import switchUID
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

    hostname = userid.split('@', 1)[1]
    ldapcfg = ldapconfig.LDAPConfig(
        baseDN=config.getDNForDomain(hostname),
        serviceLocationOverrides=config.getServiceLocationOverride(),
        identitySearch='(%s=%%(name)s)' % config.getLDAPAttributeMailbox())
    checker = checkers.LDAPBindingChecker(ldapcfg)

    d = defer.maybeDeferred(checker.requestAvatarId,
                            credentials.UsernamePassword(userid, password))

    def fetchAttributes(e, *attrs):
        return e.fetch(*attrs)
    d.addCallback(fetchAttributes,
                  config.getLDAPAttributeMailbox(),
                  config.getLDAPAttributeMailHost(),
                  )
    d.addCallback(cbLoggedIn, config, env)
    return d

def only(e, attr):
    vals = e.get(attr, None)
    if vals is None:
        raise BadUserData, "User %s has no attribute %r" % (e.dn, attr)
    if len(vals) != 1:
        raise BadUserData, \
              "User %s has too many values for attribute %r" \
              % (e.dn, attr)

    val = vals.pop()
    return val

def cbLoggedIn(e, config, env):
    mail = only(e, config.getLDAPAttributeMailbox())
    username = mail.split('@', 1)[0]
    hostname = mail.split('@', 1)[1]

    username = quot(username)
    hostname = quot(hostname)

    userpad = (username+'__')[:2]

    mailhost = only(e, config.getLDAPAttributeMailHost())

    userdir = os.path.join(config.getSpool(),
                           hostname,
                           mailhost,
                           userpad)

    env['MAILDIR'] = '.'
    env['AUTHENTICATED'] = mail
    return (userdir, username)

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
            r = util.wait(d, timeout=60.0)
            userdir, username = r

            switchUID(uid=pwd.getpwnam('scalemail')[2],
                      gid=grp.getgrnam('scalemail')[2])

            if not os.path.isdir(userdir):
                os.mkdir(userdir, 0700)
            os.chdir(userdir)

            if not os.path.isdir(username):
                initializeMaildir(username)
            os.chdir(username)

            os.execlp(sys.argv[1], *sys.argv[1:])
            die("Something is very wrong")
        except (error.UnauthorizedLogin,
                ChainLogin):
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
