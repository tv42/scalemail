from scalemail.gone import parse, times

def is_active(config, entry, now):
    l = []
    for s in entry.get(config.getLDAPAttributeAway(), []):
        gone = parse.parse(s)
        l.append(gone)
    return times.findTime(now, l)
