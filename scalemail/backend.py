"""
I am the support module for running a Scalemail SMTP server with twistd --python.
"""

from twisted.application import service, internet
from scalemail import smtp, virtual, config

# TODO make Application accept string uid/gid.
import pwd, grp
application = service.Application(
    name='scalemail',
    uid=pwd.getpwnam('scalemail')[2],
    gid=grp.getgrnam('scalemail')[2],
    )

cfg = config.ScalemailConfig()
prot = smtp.ScalemailSMTPFactory(
    spool=cfg.getSpool(),
    config=cfg,
    )

smtp = internet.TCPServer(cfg.getSMTPPort(), prot)
smtp.setServiceParent(application)

prot = virtual.ScalemailVirtualMapFactory(cfg)

virtualmap = internet.TCPServer(
    port=cfg.getPostfixVirtualMapPort(),
    factory=prot,
    interface=cfg.getPostfixVirtualMapInterface(),
    )
virtualmap.setServiceParent(application)
