"""
I am the support module for running a Scalemail SMTP server with twistd --python.
"""

from twisted.internet import app
from scalemail import smtp, virtual, config

# TODO make Application accept string uid/gid.
import pwd, grp
application = app.Application('scalemail',
                              uid=pwd.getpwnam('scalemail')[2],
                              gid=grp.getgrnam('scalemail')[2])

cfg = config.ScalemailConfig()
prot = smtp.ScalemailSMTPFactory(
    spool=cfg.getSpool(),
    config=cfg)

application.listenTCP(cfg.getSMTPPort(), prot)

prot = virtual.ScalemailVirtualMapFactory(cfg)

application.listenTCP(cfg.getPostfixVirtualMapPort(), prot,
                      interface = cfg.getPostfixVirtualMapInterface())
