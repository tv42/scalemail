import os
from twisted.protocols import postfix
from twisted.internet import protocol, defer
from twisted.python import plugin
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

    def _getAccount(self, config, local, domain):
        return util.getAccount(config, local, domain)

    def get(self, key):
        if '@' not in key:
            box, domain = util.host_split(key)

            if box is not None:
                # box.scalemail.example.com
                # tell postfix this isn't a virtual domain,
                # so it will obey transports
                return

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

            if not host:
                # "foo@", no way it'll ever match anything, claim it's
                # not found
                return None

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

            d = self.callMappers('pre',
                                 config=self.config,
                                 local=local,
                                 domain=domain)
            def _afterPreMappers(answer, callMappers, config, local, domain):
                if answer is not None:
                    return answer
                d = self._getAccount(config, local, domain)

                def _gotAccount(account, callMappers, *a, **kw):
                    d = callMappers('post', account=account, *a, **kw)
                    return d
                d.addCallback(_gotAccount, callMappers, config=self.config, local=local, domain=domain)
                return d
            d.addCallback(_afterPreMappers, self.callMappers, self.config, local, domain)

            def _joinAnswer(answer):
                if answer is not None:
                    answer = ', '.join(answer)
                return answer
            d.addCallback(_joinAnswer)

            def _fail(fail):
                fail.trap(util.ScaleMailAccountNotFound)
                return None
            d.addErrback(_fail)
            return d

    def getMappers(self, key):
        mappers = []
        for plug in plugin.getPlugIns('Scalemail.mapper.virtual.%s' % key):
            module = plug.load()
            mapper = getattr(module, 'scalemailMapper')
            pri = getattr(mapper, 'priority', 50)
            mappers.append((pri, mapper))
        mappers.sort()
        return [mapper for (pri, mapper) in mappers]

    def callMappers(self, key, *a, **kw):
        def _callMapperIfNoAnswer(answer, mapper, *a, **kw):
            if answer is not None:
                return answer
            else:
                return mapper(*a, **kw)

        d = defer.Deferred()
        for mapper in self.getMappers(key):
            d.addCallback(_callMapperIfNoAnswer, mapper, *a, **kw)
        d.callback(None)
        return d
