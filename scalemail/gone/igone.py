from zope.interface import Interface

class IRealWorld(Interface):
    def currentTime(self):
        """Return the current time, as seconds since epoch."""
        pass

    def uniqueIdentifier(self):
        """
        @return: A unique identifier for this process instance.

        The identifier must not contain a period.

        The process PID is often a good choice for blocking
        applications; e.g. twisted applications need something
        stronger.
        """
        pass

class IMessage(Interface):
    def getMessage(self):
        """
        @return: The message.
        @rtype: email.Message

        The envelope sender, as gettable with .get_unixfrom(), _must_
        be set.
        """
        pass

class RateExceededError(Exception):
    """Sender %(sender)s rate limit exceeded"""

    def __init__(self, sender):
        Exception.__init__(self)
        self.sender = sender

    def __str__(self):
        return self.__doc__ % {'sender': self.sender}
