import os
from twisted.protocols import postfix
from twisted.internet import protocol
from scalemail import util

class ScalemailVirtualMapImpossibleDomain(Exception):
    """This cannot happen"""

    def __init__(self, key, box, domain):
        Exception.__init__(self)
        self.key = key
        self.box = box
        self.domain = domain

    def __str__(self):
        return '%s: %r was parsed into %r and %r.' % (
            self.__doc__, self.key, self.box, self.domain)

class ScalemailVirtualMapFactory(protocol.ServerFactory):
    protocol = postfix.PostfixTCPMapServer

    def __init__(self, config):
        self.config = config

    def domainExists(self, rawDomain):
        domain = util.quot(rawDomain)
        if os.path.isdir(os.path.join(
            self.config.getSpool(),
            domain)):
            return True
        else:
            return False

    def get(self, key):
        if '@' not in key:
            box, domain = util.host_split(key)

            # example.com or scalemail.example.com
            if domain is None:
                # example.com
                domain = util.quot(key)
            if self.domainExists(domain):
                return 'DOMAINEXISTS'
            else:
                return None
        else:
            local, host = key.split('@', 1)
            box, domain = util.host_split(host)

            if box is not None and domain is None:
                raise ScalemailVirtualMapImpossibleDomain, \
                      (key, box, domain)

            if domain is None:
                # local@example.com
                # handle just like local@scalemail.example.com
                domain = util.quot(host)

            if not self.domainExists(domain):
                # local@scalemail.example.com, where example.com is not known
                return None

            if box is not None:
                # local@box.scalemail.example.com
                # no need to rewrite, claim it's not found
                return None

            # local@scalemail.example.com
            # -> local@box.scalemail.example.com
            d = util.getAccount(self.config, local, domain)

            def _gotAccount(account, config, local, domain):
                fwd = []
                fwd.extend(account.get(config.getLDAPAttributeMailForward(), []))
                if not fwd:
                    box = util.getRandomBox(account, config)
                    if box is not None:
                        fwd.append(local + '@' + box + '.scalemail.' + domain)
                fwd.extend(account.get(config.getLDAPAttributeMailForwardCopy(), []))
                if not fwd:
                    return None
                return ', '.join(fwd)

            d.addCallback(_gotAccount, self.config, local, domain)
            def _fail(fail):
                fail.trap(util.ScaleMailAccountNotFound)
                return None
            d.addErrback(_fail)
            return d
