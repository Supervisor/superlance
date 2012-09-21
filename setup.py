import os
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
      version='0.7',
      description='superlance plugins for supervisord',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Development Status :: 3 - Alpha",
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Topic :: System :: Boot',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Systems Administration',
        ],
      author='Chris McDonough',
      author_email='chrism@plope.com',
      maintainer = "Mike Naberezny",
      maintainer_email = "mike@naberezny.com",
      url='http://supervisord.org',
      keywords = 'supervisor monitoring',
      packages = find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
            'setuptools',
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

