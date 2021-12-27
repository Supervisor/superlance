2.0.0 (2021-12-26)
------------------

- Support for Python 2.6 has been dropped.  On Python 2, Superlance
  now requires Python 2.7.

- Support for Python 3.2 and 3.3 has been dropped.  On Python 3, Superlance
  now requires Python 3.4 or later.

- Fixed a bug introduced in 0.10 where if the timeout value is shorter
  than the time to wait between retries, the httpok check never executed.
  Issue #110.

- Fixed a bug where ``crashmailbatch`` and ``fatalmatchbatch`` did not set
  the intended default subject.  Patch by Joe Portela.

- Added a new ``--tls`` option to ``crashmailbatch``, ``fatalmailbath``, and
  ``crashsms`` to use Transport Layer Security (TLS).  Patch by Zhe Li.

1.0.0 (2016-10-02)
------------------

- Support for Python 2.5 has been dropped.  On Python 2, Superlance
  now requires Python 2.6 or later.

- Support for Python 3 has been added.  On Python 3, Superlance
  requires Python 3.2 or later.

- Fixed parsing of ``-n`` and ``--name`` options in ``httpok``.  Patch
  by DenisBY.

0.14 (2016-09-24)
-----------------

- Fixed docs build.

0.13 (2016-09-05)
-----------------

- ``httpok`` now allows multiple expected status codes to be specified.  Patch
  by valmiRe.

- ``httpok`` now has a ``--name`` option like ``memmon``.

- All commands now return exit status 0 from ``--help``.

0.12 (2016-09-03)
-----------------

- Fixed ``crashmail`` parsing of ``--optionalheader``.  Patch by Matt Dziuban.

0.11 (2014-08-15)
-----------------

- Added support for ``memmon`` to check against cumulative RSS of a process
  and all its child processes.  Patch by Lukas Graf.

- Fixed a bug introduced in 0.9 where the ``-u`` and ``-n`` options in
  ``memmon`` were parsed incorrectly.  Patch by Harald Friessnegger.

0.10 (2014-07-08)
-----------------

- Honor timeout in httok checks even on trying the connection.
  Without it, processes that take make than 60 seconds to accept connections
  and http_ok with TICK_60 events cause a permanent restart of the process.

- ``httpok`` now sends a ``User-Agent`` header of ``httpok``.

- Removed ``setuptools`` from the ``requires`` list in ``setup.py`` because
  it caused installation issues on some systems.

0.9 (2013-09-18)
----------------

- Added license.

- Fixed bug in cmd line option validator for ProcessStateEmailMonitor
  Bug report by Val Jordan

- Added ``-u`` option to memmon the only send an email in case the restarted
  process' uptime (in seconds) is below this limit.  This is useful to only
  get notified if a processes gets restarted too frequently.
  Patch by Harald Friessnegger.

0.8 (2013-05-26)
----------------

- Superlance will now refuse to install on an unsupported version of Python.

- Allow SMTP credentials to be supplied to ProcessStateEmailMonitor
  Patch by Steven Davidson.

- Added ``-n`` option to memmon that adds this name to the email
  subject to identify which memmon process restarted a process.
  Useful in case you run multiple supervisors that control
  different processes with the same name.
  Patch by Harald Friessnegger.

- ProcessStateEmailMonitor now adds Date and Message-ID headers to emails.
  Patch by Andrei Vereha.

0.7 (2012-08-22)
----------------

- The ``crashmailbatch --toEmail`` option now accepts a comma-separated
  list of email addresses.

0.6 (2011-08-27)
----------------

- Separated unit tests into their own files

- Created ``fatalmailbatch`` plugin

- Created ``crashmailbatch`` plugin

- Sphinxified documentation.

- Fixed ``test_suite`` to use the correct module name in setup.py.

- Fixed the tests for ``memmon`` to import the correct module.

- Applied patch from Sam Bartlett: processes which are not autostarted
  have pid "0".  This was crashing ``memmon``.

- Add ``smtpHost`` command line flag to ``mailbatch`` processors.

- Added ``crashsms`` from Juan Batiz-Benet

- Converted ``crashmailbatch`` and friends from camel case to pythonic style

- Fixed a bug where ``httpok`` would crash with the ``-b`` (in-body)
  option.  Patch by Joaquin Cuenca Abela.

- Fixed a bug where ``httpok`` would not handle a URL with a query string
  correctly.  Patch by Joaquin Cuenca Abela.

- Fixed a bug where ``httpok`` would not handle process names with a
  group ("group:process") properly.  Patch by Joaquin Cuenca Abela.


0.5 (2009-05-24)
----------------

- Added the ``memmon`` plugin, originally bundled with supervisor and
  now moved to superlance.


0.4 (2009-02-11)
----------------

- Added ``eager`` and ``not-eager`` options to the ``httpok`` plugin.

  If ``not-eager`` is set, and no process being monitored is in the
  ``RUNNING`` state, skip the URL check / mail message.


0.3 (2008-12-10)
----------------

- Added ``gcore`` and ``coredir`` options to the ``httpok`` plugin.


0.2 (2008-11-21)
----------------

- Added the ``crashmail`` plugin.


0.1 (2008-09-18)
----------------

- Initial release
