#!/usr/bin/env python

#debian-section: mail

import os.path
from distutils.core import setup, Extension
from distutils.sysconfig import get_python_lib

if __name__=='__main__':
    setup(name="scalemail",
	  description="Scalable virtual mail domain system built on Postfix and LDAP",
	  long_description="""

A scalable (but not HA, at least not yet) virtual domain system for
handling mail for many users, based on Postfix, LDAP, Courier-IMAP,
Python and Twisted.

""".strip(),
	  author="Tommi Virtanen",
	  author_email="tv@debian.org",
	  url="http://scalemail.sourceforge.net/",
	  licence="GNU GPL",

	  packages=[
	"scalemail",
	],
          data_files=[('/etc/scalemail',
                       ["scalemail.conf"]),
                      ('/etc/ldap/schema',
                       ["scalemail.schema"]),
                      ('/usr/lib/courier/authlib',
                       ["scalemail-courier-login-mapper"]),
                      ],
	  )
