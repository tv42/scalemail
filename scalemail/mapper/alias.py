from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap import ldapsyntax
from scalemail import util

class AccountExistsGetter(util.AccountGetter):
    def _fetch(self, proto):
        dn = self.config.getDNForDomain(self.domain)
        o = ldapsyntax.LDAPEntry(client=proto, dn=dn)
        ldapAttributeAlias=self.config.getLDAPAttributeAlias()
        ldapAttributeMailbox=self.config.getLDAPAttributeMailbox()
        target = self.user+'@'+self.domain

        d=o.search(filterObject=pureldap.LDAPFilter_or([

            # alias
            pureldap.LDAPFilter_and([
            pureldap.LDAPFilter_equalityMatch(
            attributeDesc=pureldap.LDAPAttributeDescription(ldapAttributeAlias),
            assertionValue=pureldap.LDAPAssertionValue(target)),
            # must have mail attribute or we cannot forward it
            pureldap.LDAPFilter_present(ldapAttributeMailbox),

            ]),

            # real entry that conflicts with alias
            pureldap.LDAPFilter_equalityMatch(
            attributeDesc=pureldap.LDAPAttributeDescription(ldapAttributeMailbox),
            assertionValue=pureldap.LDAPAssertionValue(target)),
            
            ]))

        d.addBoth(self._unbind, proto)
        return d

    def _searchCompleted(self, entries):
        target = self.user+'@'+self.domain
        alias = []
        real = []

        ldapAttributeAlias=self.config.getLDAPAttributeAlias()
        ldapAttributeMailbox=self.config.getLDAPAttributeMailbox()

        for e in entries:
            if target in e.get(ldapAttributeMailbox, []):
                real.append(e)
            elif target in e.get(ldapAttributeAlias, []):
                alias.append(e)

        if alias and real:
            raise util.ScaleMailAccountMultipleEntries

        if not alias:
            return None
        else:
            l = []
            for e in alias:
                l.extend(e[ldapAttributeMailbox])
            return l

def scalemailMapper(config, local, domain):
    f = AccountExistsGetter(config, local, domain)
    d = f.getAccount()
    return d

scalemailMapper.priority = 10
