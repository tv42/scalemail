import os
from scalemail.gone import igone

class RateDir(object):

    count = 1
    interval = 1*60*60
    path = None

    def __init__(self, world, path, count=None, interval=None,
                 *a, **kw):
        super(RateDir, self).__init__(*a, **kw)
        self.world = world
        self.path = path
        if count is not None:
            self.count = count
        if interval is not None:
            self.interval = interval

    def _mangle(self, sender):
        return sender.replace('/', ':')

    def _filename(self, sender, now):
        return '%s.%u.%s' % (self.world.uniqueIdentifier(),
                             now,
                             self._mangle(sender))

    def _mark(self, sender, now, last_filename=None):
        filename = self._filename(sender, now)

        if last_filename is not None:
            # hard link to save inodes
            try:
                os.link(os.path.join(self.path, last_filename),
                        os.path.join(self.path, filename))
            except OSError:
                # on error, fall back to creating a new file
                pass
            else:
                return

        fd = os.open(os.path.join(self.path, filename),
                     os.O_WRONLY|os.O_CREAT|os.O_EXCL,
                     0444)
        os.close(fd)

    def tick(self, sender):
        """
        Add one message to rate tracking for sender at time now.

        @raise RateExceededError: If rate limit would be exceeded.

        For each entry in directory listing:
        - split filename into TIMESTAMP, PID, ADDRESS parts
        - ignore filenames that don't match these parts
        - if (NOW-TIMESTAMP) > INTERVAL: remove file and ignore
        - if ADDRESS == SENDER:
        - add one to Rate
        - if Rate is above maximum, fail without creating another file
        - Create a new file in the directory, named as above, optionally using a
        link instead of a new file to preserve inodes.
        - Return RATE+1 (add one for the current message)
        """
        count = 0
        last_filename = None
        now = self.world.currentTime()

        for filename in os.listdir(self.path):
            if filename.startswith('.'):
                continue
            l = filename.split('.', 2)
            if len(l) != 3:
                continue
            id_, time, address = l
            try:
                time = int(time)
            except ValueError:
                continue

            if now - time > self.interval:
                # clean up old entries
                try:
                    os.unlink(os.path.join(self.path, filename))
                except OSError:
                    pass
            else:
                if address.upper() == sender.upper():
                    count += 1
                    if count >= self.count:
                        raise igone.RateExceededError, sender
                last_filename = filename

        # TODO ponder is it better to mark _after_
        # a succesful send -- it's not atomic either
        # way, which one is better?
        self._mark(sender, now, last_filename)
