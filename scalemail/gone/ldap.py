from scalemail.gone import parse, times, respond

def is_active(cfg, e, now):
    l = []
    for s in e.get(cfg.getLDAPAttributeAway(), []):
        gone = parse.parse(s)
        l.append(gone)
    return times.findTime(now, l)
