from scalemail import util

def scalemailMapper(config, account, local, domain):
    # local@scalemail.example.com
    # -> local@box.scalemail.example.com
    fwd = []
    fwd.extend(account.get(config.getLDAPAttributeMailForward(), []))
    if not fwd:
        return None
    fwd.extend(account.get(config.getLDAPAttributeMailForwardCopy(), []))
    return fwd

scalemailMapper.priority = 10
