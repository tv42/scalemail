from scalemail import util

def scalemailMapper(config, account, local, domain):
    # local@scalemail.example.com
    # -> local@box.scalemail.example.com
    fwd = []
    box = util.getRandomBox(account, config)
    if box is not None:
        fwd.append(local + '@' + box + '.scalemail.' + domain)
    fwd.extend(account.get(config.getLDAPAttributeMailForwardCopy(), []))
    if not fwd:
        return None
    return fwd

scalemailMapper.priority = 20
