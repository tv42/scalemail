from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap import ldapsyntax
from scalemail import util

class AccountExistsGetter(util.AccountGetter):
    def _fetch(self, proto):
        dn = self.config.getDNForDomain(self.domain)
        o = ldapsyntax.LDAPEntry(client=proto, dn=dn)
        ldapAttributeAlias=self.config.getLDAPAttributeAlias()
        ldapAttributeMailbox=self.config.getLDAPAttributeMailbox()
        d=o.search(filterObject=pureldap.LDAPFilter_and([
            pureldap.LDAPFilter_equalityMatch(
            attributeDesc=pureldap.LDAPAttributeDescription(ldapAttributeAlias),
            assertionValue=pureldap.LDAPAssertionValue(self.user+'@'+self.domain)),

            pureldap.LDAPFilter_present(ldapAttributeMailbox),

            ]))

        d.addBoth(self._unbind, proto)
        return d

    def _searchCompleted(self, entries):
        if not entries:
            return None
        else:
            ldapAttributeMailbox=self.config.getLDAPAttributeMailbox()
            l = []
            for e in entries:
                l.extend(e[ldapAttributeMailbox])
            return l

def scalemailMapper(config, local, domain):
    f = AccountExistsGetter(config, local, domain)
    d = f.getAccount()
    return d

scalemailMapper.priority = 10
