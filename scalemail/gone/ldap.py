from scalemail.gone import parse, times, respond

def is_active(e, now):
    l = []
    for s in e.get('scaleMailAway', []):
        gone = parse.parse(s)
        l.append(gone)
    return times.findTime(now, l)
