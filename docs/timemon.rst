:command:`timemon` Overview
==========================

:command:`timemon` is a supervisor "event listener" which may be subscribed to
a concrete ``TICK_x`` event. When :command:`memmon` receives a ``TICK_x``
event (``TICK_3600`` is recommended, indicating activity every hour),
:command:`timemon` restarts all programs in given group every N hours

:command:`timemon` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`timemon` is an executable program, it
isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

:command:`timemon` uses Supervisor's XML-RPC interface.  Your ``supervisord.conf``
file must have a valid `[unix_http_server]
<http://supervisord.org/configuration.html#unix-http-server-section-settings>`_
or `[inet_http_server]
<http://supervisord.org/configuration.html#inet-http-server-section-settings>`_
section, and must have an `[rpcinterface:supervisor]
<http://supervisord.org/configuration.html#rpcinterface-x-section-settings>`_
section.  If you are able to control your ``supervisord`` instance with
``supervisorctl``, you have already met these requirements.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ timemon -g groupname -i hour -n every_n_hours

.. program:: timemon

.. cmdoption:: -h, --help

   Show program help.

.. cmdoption:: -g, --group

   Process group to restart

.. cmdoption:: -i, --interval

   Interval (minute or hour)

.. cmdoption:: -n, --number

    How many intervals should be between program restarts. For example `-i minute -n 6` - restarts every 6 minutes


Configuring :command:`timemon` Into the Supervisor Config
--------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`timemon` to do its work. See the "Events" chapter in the
Supervisor manual for more information about event listeners.

The following examples assume that :command:`timemon` is on your system
:envvar:`PATH`.

Example Configuration
#####################

This configuration causes :command:`memmon` to restart any process which is
a child of :command:`supervisord` consuming more than 200MB of RSS, and will
send mail to ``bob@example.com`` when it restarts a process using the
default :command:`sendmail` command.

.. code-block:: ini

   [eventlistener:timemon]
   command=timemon -g procellgroup -i hour -n 3
   events=TICK_3600


