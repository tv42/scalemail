import ConfigParser
from ldaptor.protocols.ldap import distinguishedname

class ScalemailConfig:
    config = None

    def __init__(self):
        self.load()

    def load(self):
        C=getattr(ConfigParser, 'SafeConfigParser', ConfigParser.ConfigParser)
        config = C({
            'spool': '/var/spool/scalemail',
            'ldap-attribute-mail': 'mail',
            'ldap-attribute-mailhost': 'scaleMailHost',
            'ldap-attribute-mailquota': 'scaleMailQuota',
            'smtp-port': '8025',
            'recipient-delimiters': '+',
            })

        config.read('/etc/scalemail/scalemail.conf')

        try:
            config.add_section('Scalemail')
        except ConfigParser.DuplicateSectionError:
            pass
        self.config = config

    def getSpool(self):
        return self.config.get('Scalemail', 'spool')

    def getLDAPAttributeMailbox(self):
        return self.config.get('Scalemail', 'ldap-attribute-mail')

    def getLDAPAttributeMailHost(self):
        return self.config.get('Scalemail', 'ldap-attribute-mailhost')

    def getLDAPAttributeMailQuote(self):
        return self.config.get('Scalemail', 'ldap-attribute-mailquota')

    def getRecipientDelimiters(self):
        return self.config.get('Scalemail', 'recipient-delimiters')

    def getSMTPPort(self):
        return self.config.getint('Scalemail', 'smtp-port')

    def getDNForDomain(self, domain):
        key = 'map-domain %s' % domain
        if (self.config.has_section('BaseDN')
            and self.config.has_option('BaseDN', key)):
            dnString = self.config.get('BaseDN', key)
        else:
            domainComponents = domain.split('.')
            dnString = ','.join(['dc=%s'%dc for dc in domainComponents])
        dn = distinguishedname.DistinguishedName(stringValue=dnString)
        return dn

    def getServiceLocationOverride(self):
        serviceLocationOverride = {}
        for section in self.config.sections():
            if section.lower().startswith('service-location '):
                base = section[len('service-location '):].strip()

                host = None
                if self.config.has_option(section, 'host'):
                    host = self.config.get(section, 'host')
                    if not host:
                        host = None

                port = None
                if self.config.has_option(section, 'port'):
                    port = self.config.get(section, 'port')
                    if not port:
                        port = None

                dn = distinguishedname.DistinguishedName(stringValue=base)
                serviceLocationOverride[dn]=(host, port)
        return serviceLocationOverride
