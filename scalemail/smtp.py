import errno
from twisted.protocols import smtp
from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap import ldapclient, ldapsyntax, distinguishedname, ldapconnector
from twisted.mail import maildir, protocols
from twisted.internet import protocol, reactor, defer
from scalemail import util
import os.path

def maildirmake(dir):
    maildir.initializeMaildir(dir)

def mailfoldermake(dir):
    if not os.path.isdir(dir):
        os.mkdir(dir, 0700)
        for subdir in ['new', 'cur', 'tmp']:
            os.mkdir(os.path.join(dir, subdir), 0700)
    f=open(os.path.join(dir, "maildirfolder"), 'a')
    f.close()

def _user_prefix(username):
    return (username[:2]+"__")[:2]

class ScalemailMaildirDomain(maildir.AbstractMaildirDomain):
    """TODO"""

    """
    TODO quota logic:


    getquotabydn () {
    DN="$1"

    QUO=""
    # TODO get a better comparison, whitespace can confuse this one
    while [ ! "$QUO" -a "$DN" != "$CONFIG_LDAP_SEARCH_BASE" ]; do
	# Eww..
	QUO="$(ldapsearch -x -LLL -s base -b "$DN" \
	    "$CONFIG_LDAP_ATTRIBUTES_MAILQUOTA=*" "$CONFIG_LDAP_ATTRIBUTES_MAILQUOTA" \
	    |sed -n "s/^$CONFIG_LDAP_ATTRIBUTES_MAILQUOTA: *//p")" \
	|| exit $EX_TEMPFAIL
	DN="${DN#*,}"
	if [ "$DN" = "" ]; then
	    echo "$0: bug, getquotabydn made dn empty while input was $1, end." 1>&2
	    exit $EX_TEMPFAIL
	fi
    done

    echo "$QUO"
}


	# 3. store mail in $DOMAIN/$BOX/$USER/.$FOLDER/ or #
        # $DOMAIN/$BOX/$USER/ with deliverquota (fetch quota from
        # LDAP, cache on disk for 24 hours)

        # exists and is newer than 24 hours
        if [ -e "$MAILDIR/quota" \
             -a ! "$(find "$MAILDIR/quota" -mtime +1)" ]; then
	read QUO <"$MAILDIR/quota"
        else
	# fetch dn if not already fetched
                [ "$DN" ] || DN="$(getdnbymaildrop "$USER" "$DOMAIN" "$BOX")"

                QUO="$(getquotabydn "$DN")"

                # store $QUO to $MAILDIR/quota. This is a bit ugly :(
                echo "$QUO" >"$MAILDIR/quota.$$.tmp" \
                     || exit $EX_TEMPFAIL
                mv "$MAILDIR/quota.$$.tmp" "$MAILDIR/quota" \
                   || exit $EX_TEMPFAIL
	fi
        "
"""

    def __init__(self, service, root,
                 box, domain,
                 config):
        maildir.AbstractMaildirDomain.__init__(self, service, root)
        self.box = box
        self.domain = domain
        self.config = config

    def _userdir_prefix(self, username):
        username, folder = util.addr_split(username, self.config.getRecipientDelimiters())
        return os.path.join(self.root, _user_prefix(username))

    def _userdir(self, username):
        username, folder = util.addr_split(username, self.config.getRecipientDelimiters())
        return (os.path.join(self._userdir_prefix(username), username), folder)

    def exists(self, user, memo=None):
        if self.userDirectory(user.dest.local) is not None:
            return lambda: self.startMessage(user)
        else:
            # do the LDAP dance and make sure the dir gets created
            d = self.ldapUserExists(user.dest.local)
            def _cb(found):
                if found:
                    return lambda: self.startMessage(user)
                else:
                    raise smtp.SMTPBadRcpt, (
                        user, 550, 'User not found in LDAP.')
            d.addCallback(_cb)
            return d

    def ldapUserExists(self, username):
        username, folder = util.addr_split(username, self.config.getRecipientDelimiters())

        dn = self.config.getDNForDomain(self.domain)
        c=ldapconnector.LDAPClientCreator(reactor, ldapclient.LDAPClient)
        d=c.connect(dn, self.config.getServiceLocationOverride())

        def _bind(proto):
            d=proto.bind()
            d.addCallback(lambda _: proto)
            return d

        d.addCallback(_bind)

        def _search(proto,
                    user, box, domain,
                    ldapAttributeMailbox, ldapAttributeMailHost,
                    dn):
            o = ldapsyntax.LDAPEntry(client=proto, dn=dn)

            d=o.search(filterObject=pureldap.LDAPFilter_and(
                [

                pureldap.LDAPFilter_equalityMatch(
                attributeDesc=pureldap.LDAPAttributeDescription(ldapAttributeMailbox),
                assertionValue=pureldap.LDAPAssertionValue(user+'@'+domain)),

                pureldap.LDAPFilter_equalityMatch(
                attributeDesc=pureldap.LDAPAttributeDescription(ldapAttributeMailHost),
                assertionValue=pureldap.LDAPAssertionValue(box)),

                ]),
                       typesOnly=1,
                       attributes=[self.config.getLDAPAttributeAway()],
                       sizeLimit=1)

            def _unbind(entries, proto):
                proto.unbind()
                return entries
            d.addCallback(_unbind, proto)

            return d

        d.addCallback(_search,
                      user=username, box=self.box, domain=self.domain,
                      ldapAttributeMailbox=self.config.getLDAPAttributeMailbox(),
                      ldapAttributeMailHost=self.config.getLDAPAttributeMailHost(),
                      dn=self.config.getDNForDomain(self.domain))

        def _found(exists, prefix, dir):
            if exists:
                try:
                    os.mkdir(prefix, 0700)
                except OSError, err:
                    if err.errno!=errno.EEXIST:
                        raise
                maildirmake(dir)
            return exists

        d.addCallback(_found,
                      self._userdir_prefix(username),
                      self._userdir(username)[0])

        def _fail(_):
            raise smtp.SMTPServerError, (451,
                                         'Error contacting the LDAP server: %s'
                                         % reason.getErrorMessage())
        d.addErrback(_fail)
        return d

    def userDirectory(self, username):
        """Get the maildir directory for a given user

        Return None for non-existing users.
        """
        (dir, folder)=self._userdir(username)
        if not os.path.isdir(dir):
            return None
        if folder:
            dir=os.path.join(dir, '.'+folder)
            if not os.path.isdir(dir):
                mailfoldermake(dir)
        return dir

class ScalemailDelivery(protocols.ESMTPDomainDelivery):
    def __init__(self, proto):
        self.proto = proto
        protocols.ESMTPDomainDelivery.__init__(self, service=None, user=None)

    def validateTo(self, user):
        if not user.dest.domain:
            raise smtp.SMTPBadRcpt, (user, 550, 'No domain name given')

        # test whether such host dir exists
        box, domain=util.host_split(user.dest.domain)

        if domain is None:
            raise smtp.SMTPBadRcpt, (user, 550, 'Invalid domain name given: %r' % user.dest.domain)

        if box is None:
            d = self._userBelongsToMe(user, domain)
        else:
            d = defer.succeed(box)

        d.addCallback(self._cbGotBox, domain, user)
        return d

    def _userBelongsToMe(self, user, domain):
        """

        Test whether given user belongs to this backend box.

        Return a deferred that becomes the box name if he does, fail
        with SMTPBadRcpt is he does not.

        """
        root=os.path.join(self.proto.factory.spool, domain)
        d = util.getAccount(config=self.proto.factory.config,
                            local=user.dest.local,
                            domain=domain)
        d.addCallback(util.getBoxes, config=self.proto.factory.config)

        def _cbGotBoxes(boxes,
                        root,
                        user, domain):
            if not boxes:
                raise smtp.SMTPBadRcpt, (
                    user+'@'+domain,
                    550,
                    'User is not served by any scalemail backend.')
            for box in boxes:
                if os.path.isdir(os.path.join(root, box)):
                    # this host serves this backend
                    # -> user belongs to us
                    # -> accept mail
                    return box
            raise smtp.SMTPBadRcpt, (
                user+'@'+domain,
                550,
                'User is not served by this scalemail backend.')

        d.addCallback(_cbGotBoxes,
                      root=root,
                      user=user.dest.local, domain=domain)

        def _setDomain(box, user):
            user.dest.domain = box + '.' + user.dest.domain
            return box

        d.addCallback(_setDomain, user)

        def _fail(reason):
            raise smtp.SMTPServerError, (451,
                                         'Error contacting the LDAP server: %s'
                                         % reason.getErrorMessage())
        d.addErrback(_fail)
        return d

    def _cbGotBox(self, box, domain, user):
        dir=os.path.join(self.proto.factory.spool, domain, box)
        if os.path.isdir(dir):
            # domain is valid
            dom=ScalemailMaildirDomain(None, #TODO
                                       dir,
                                       box, domain,
                                       self.proto.factory.config)
            return dom.exists(user)
        else:
            raise smtp.SMTPBadRcpt, (user, 550, 'Domain name given not served here: %r' % user.dest.domain)

class ScalemailSMTP(smtp.ESMTP):
    factory = None # to please pychecker

    def __init__(self):
        smtp.ESMTP.__init__(self)
        self.delivery = ScalemailDelivery(self)

    def __repr__(self):
        return '<%s>' % self.__class__.__name__

class ScalemailSMTPFactory(smtp.SMTPFactory):
    protocol = ScalemailSMTP

    def __init__(self, spool,
                 config,
                 ):
        smtp.SMTPFactory.__init__(self, portal=None)
        self.spool=spool
        self.config=config
        self.domain = 'scalemail.%s' % self.domain

def calltrace():
    def printfuncnames(frame, event, dummy_arg):
        print "|%s: %s:%d:%s" % (event,
                                 frame.f_code.co_filename,
                                 frame.f_code.co_firstlineno,
                                 frame.f_code.co_name)
    import sys
    sys.setprofile(printfuncnames)
