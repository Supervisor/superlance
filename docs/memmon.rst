:command:`memmon` Overview
==========================

:command:`memmon` is a supervisor "event listener" which may be subscribed to
a concrete ``TICK_x`` event. When :command:`memmon` receives a ``TICK_x``
event (``TICK_60`` is recommended, indicating activity every 60 seconds),
:command:`memmon` checks that a configurable list of programs (or all
programs running under supervisor) are not exceeding a configurable about of
memory (resident segment size, or RSS).  If one or more of these processes is
consuming more than the amount of memory that :command:`memmon` believes it
should, :command:`memmon` will restart the process. :command:`memmon` can be
configured to send an email notification when it restarts a process.

:command:`memmon` is known to work on Linux and Mac OS X, but has not been
tested on other operating systems (it relies on :command:`ps` output and
command-line switches).

:command:`memmon` is incapable of monitoring the process status of processes
which are not :command:`supervisord` child processes.

:command:`memmon` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`memmon` is an executable program, it
isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ memmon [-p processname=byte_size] [-g groupname=byte_size] \
            [-a byte_size] [-s sendmail] [-m email_address] [-n memmon_name]

.. program:: memmon

.. cmdoption:: -h, --help

   Show program help.

.. cmdoption:: -p <name/size pair>, --program=<name/size pair>

   A name/size pair, e.g. "foo=1MB". The name represents the supervisor
   program name that you would like :command:`memmon` to monitor; the size
   represents the number of bytes (suffix-multiplied using "KB", "MB" or "GB")
   that should be considered "too much".

   This option can be provided more than once to have :command:`memmon`
   monitor more than one program.

   Programs can be specified using a "namespec", to disambiguate same-named
   programs in different groups, e.g. ``foo:bar`` represents the program
   ``bar`` in the ``foo`` group.

.. cmdoption:: -g <name/size pair>, --groupname=<name/size pair>

   A groupname/size pair, e.g. "group=1MB". The name represents the supervisor
   group name that you would like :command:`memmon` to monitor; the size
   represents the number of bytes (suffix-multiplied using "KB", "MB" or "GB")
   that should be considered "too much".

   Multiple ``-g`` options can be provided to have :command:`memmon` monitor
   more than one group.  If any process in this group exceeds the maximum,
   it will be restarted.

.. cmdoption:: -a <size>, --any=<size>

   A size (suffix-multiplied using "KB", "MB" or "GB") that should be
   considered "too much". If any program running as a child of supervisor
   exceeds this maximum, it will be restarted. E.g. 100MB.

.. cmdoption:: -s <command>, --sendmail=<command>

   A command that will send mail if passed the email body (including the
   headers).  Defaults to ``/usr/sbin/sendmail -t -i``.

.. note::

   Specifying this option doesn't cause memmon to send mail by itself:
   see the ``-m`` / ``--email`` option.

.. cmdoption:: -m <email address>, --email=<email address>

   An email address to which to send email when a process is restarted.
   By default, memmon will not send any mail unless an email address is
   specified.

.. cmdoption:: -n <memmon name>, --name=<memmon name>

   An optional name that identifies this memmon process. If given, the
   email subject will start with ``memmon [<memmon name>]:`` instead
   of ``memmon:``
   In case you run multiple supervisors on a single host that control
   different processes with the same name (eg `zopeinstance1`) you can
   use this option to indicate which project the restarted instance
   belongs to.



Configuring :command:`memmon` Into the Supervisor Config
--------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`memmon` to do its work. See the "Events" chapter in the
Supervisor manual for more information about event listeners.

The following examples assume that :command:`memmon` is on your system
:envvar:`PATH`.

Example Configuration 1
#######################

This configuration causes :command:`memmon` to restart any process which is
a child of :command:`supervisord` consuming more than 200MB of RSS, and will
send mail to ``bob@example.com`` when it restarts a process using the
default :command:`sendmail` command.

.. code-block:: ini

   [eventlistener:memmon]
   command=memmon -a 200MB -m bob@example.com
   events=TICK_60


Example Configuration 2
#######################

This configuration causes :command:`memmon` to restart any process with the
supervisor program name ``foo`` consuming more than 200MB of RSS, and
will send mail to ``bob@example.com`` when it restarts a process using
the default sendmail command.

.. code-block:: ini

   [eventlistener:memmon]
   command=memmon -p foo=200MB -m bob@example.com
   events=TICK_60


Example Configuration 3
#######################

This configuration causes :command:`memmon` to restart any process in the
process group "bar" consuming more than 200MB of RSS, and will send mail to
``bob@example.com`` when it restarts a process using the default
:command:`sendmail` command.

.. code-block:: ini

   [eventlistener:memmon]
   command=memmon -g bar=200MB -m bob@example.com
   events=TICK_60
