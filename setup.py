##############################################################################
#
# Copyright (c) 2008-2013 Agendaless Consulting and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE
#
##############################################################################

import os
import sys

py_version = sys.version_info[:2]

if py_version < (2, 6):
    raise RuntimeError('On Python 2, superlance requires Python 2.6 or later')
elif (3, 0) < py_version < (3, 2):
    raise RuntimeError('On Python 3, superlance requires Python 3.2 or later')

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, 'README.txt')).read()
except (IOError, OSError):
    README = ''
try:
    CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()
except (IOError, OSError):
    CHANGES = ''

setup(name='superlance',
      version='1.0.0-dev',
      license='BSD-derived (http://www.repoze.org/LICENSE.txt)',
      description='superlance plugins for supervisord',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Development Status :: 3 - Alpha",
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: System :: Boot',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Systems Administration',
        ],
      author='Chris McDonough',
      author_email='chrism@plope.com',
      maintainer = "Chris McDonough",
      maintainer_email = "chrism@plope.com",
      url='http://supervisord.org',
      keywords = 'supervisor monitoring',
      packages = find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
            'supervisor',
            ],
      tests_require=[
            'supervisor',
            'mock',
            ],
      test_suite='superlance.tests',
      entry_points = """\
      [console_scripts]
      httpok = superlance.httpok:main
      crashsms = superlance.crashsms:main
      crashmail = superlance.crashmail:main
      crashmailbatch = superlance.crashmailbatch:main
      fatalmailbatch = superlance.fatalmailbatch:main
      memmon = superlance.memmon:main
      """
      )

