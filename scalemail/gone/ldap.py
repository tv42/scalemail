from scalemail.gone import parse, times, respond

def _is_active(e, now):
    l = []
    for s in e.get('scaleMailAway', []):
        gone = parse.parse(s)
        l.append(gone)
    return times.findTime(now, l)

def is_active(e, now):
    d = e.fetch('scaleMailAway')
    d.addCallback(_is_active, now)
    return d
