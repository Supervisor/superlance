superlance plugins for supervisor
=================================

Superlance is a package of plugin utilities for monitoring and
controlling processes that run under `Supervisor
<http://supervisord.org>`_.  It provides these plugins:

:command:`httpok`
    This plugin is meant to be used as a supervisor event listener,
    subscribed to ``TICK_*`` events.  It tests that a given child process
    which must in the ``RUNNING`` state, is viable via an HTTP ``GET``
    request to a configured URL.  If the request fails or times out,
    :command:`httpok` will restart the "hung" child process.

:command:`crashmail`
    This plugin is meant to be used as a supervisor event listener,
    subscribed to ``PROCESS_STATE_EXITED`` events.  It email a user when
    a process enters the ``EXITED`` state unexpectedly.

:command:`memmon`
    This plugin is meant to be used as a supervisor event listener,
    subscribed to ``TICK_*`` events.  It monitors memory usage for configured
    child processes, and restarts them when they exceed a configured
    maximum size.

:command:`crashmailbatch`
    Similar to :command:`crashmail`, :command:`crashmailbatch` sends email
    alerts when processes die unexpectedly.  The difference is that all alerts
    generated within the configured time interval are batched together to avoid
    sending too many emails.

:command:`fatalmailbatch`
    This plugin sends email alerts when processes fail to start
    too many times such that supervisord gives up retrying.  All of the fatal
    start events generated within the configured time interval are batched
    together to avoid sending too many emails.

:command:`crashsms`
    Similar to :command:`crashmailbatch` except it sends SMS alerts
    through an email gateway.  Messages are formatted to fit in SMS.

Contents:

.. toctree::
   :maxdepth: 2

   httpok
   crashmail
   memmon
   crashmailbatch
   fatalmailbatch
   crashsms
   development

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

