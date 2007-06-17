import os, sys, pwd, grp, logging
from twisted.internet import reactor, defer
from twisted.cred import credentials, error
from twisted.mail.maildir import initializeMaildir
from twisted.python.util import switchUID
from ldaptor import checkers
from ldaptor import config as ldapconfig
from scalemail import config

log = logging.getLogger('scalemail.checkpassword')

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

def only(e, attr):
    vals = e.get(attr, None)
    if vals is None:
        raise RuntimeError(
            "User %s has no attribute %r" % (e.dn, attr))
    if len(vals) != 1:
        raise RuntimeError(
            "User %s has too many values for attribute %r" \
            % (e.dn, attr))

    val = vals.pop()
    return val

def run():
    import traceback

    logging.basicConfig()

    try:
        cfg = config.ScalemailConfig()
        authfile = os.fdopen(3, 'r')
        data = authfile.read()
        authfile.close()

        userid, password, timestamp = data.split('\0', 3)[:3]
        if not sys.argv[1:]:
            log.error("Need to provide some arguments.")
            sys.exit(2)

        userid = userid.replace('%', '@')
        if '@' not in userid:
            log.info('Tried to login without domain: %r' % userid)
            sys.exit(1)

        hostname = userid.split('@', 1)[1]
        ldapcfg = ldapconfig.LDAPConfig(
            baseDN=cfg.getDNForDomain(hostname),
            serviceLocationOverrides=cfg.getServiceLocationOverride(),
            identitySearch='(%s=%%(name)s)' % cfg.getLDAPAttributeMailbox())
        checker = checkers.LDAPBindingChecker(ldapcfg)

        d = defer.maybeDeferred(
            checker.requestAvatarId,
            credentials.UsernamePassword(userid, password))

        def ebLogin(fail):
            fail.trap(error.UnauthorizedLogin)
            sys.exit(1)
        d.addErrback(ebLogin)

        def fetchAttributes(e, config):
            return e.fetch(
                config.getLDAPAttributeMailbox(),
                config.getLDAPAttributeMailHost(),
                )
        d.addCallback(fetchAttributes, cfg)

        def cbLoggedIn(e, config):
            mail = only(e, config.getLDAPAttributeMailbox())
            username = mail.split('@', 1)[0]
            hostname = mail.split('@', 1)[1]

            username = quot(username)
            hostname = quot(hostname)

            userpad = (username+'__')[:2]

            mailhost = only(e, config.getLDAPAttributeMailHost())

            userdir = os.path.join(
                config.getSpool(),
                hostname,
                mailhost,
                userpad)

            switchUID(uid=pwd.getpwnam('scalemail')[2],
                      gid=grp.getgrnam('scalemail')[2])

            if not os.path.isdir(userdir):
                os.mkdir(userdir, 0700)
            os.chdir(userdir)

            if not os.path.isdir(username):
                initializeMaildir(username)
            os.chdir(username)

            os.execlp(sys.argv[1], *sys.argv[1:])
            print >>sys.stderr, "scalemail-courier-login: Cannot exec command."
            sys.exit(2)

        d.addCallback(cbLoggedIn, cfg)


        ERROR = []

        def ebFinal(fail):
            logging.error(fail.getErrorMessage())
            ERROR.append(fail)
        d.addErrback(ebFinal)

        def theEnd(dummy):
            reactor.callWhenRunning(reactor.stop)
            return dummy
        d.addBoth(theEnd)

        reactor.run()

        for e in ERROR:
            if e.check(SystemExit):
                raise e.value
            log.error(e.getTraceback())
            sys.exit(111)

    except SystemExit, e:
        raise
    except:
        try:
            traceback.print_exc(file=sys.stderr)
        finally:
            sys.exit(111)
