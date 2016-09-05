:command:`crashmail` Documentation
==================================

:command:`crashmail` is a supervisor "event listener", intended to be
subscribed to ``PROCESS_STATE_EXITED`` events. When :command:`crashmail`
receives that event, and the transition is "unexpected", :command:`crashmail`
sends an email notification to a configured address.

:command:`crashmail` is incapable of monitoring the process status of processes
which are not :command:`supervisord` child processes.

:command:`crashmail` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`crashmail` is an executable program, it
isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ crashmail [-p processname] [-a] [-o string] [-m mail_address] \
               [-s sendmail]

.. program:: crashmail

.. cmdoption:: -p <process_name>, --program=<process_name>

   Send mail when the specified :command:`supervisord` child process
   transitions unexpectedly to the ``EXITED`` state.

   This option can be provided more than once to have :command:`crashmail`
   monitor more than one program.

   To monitor a process which is part of a :command:`supervisord` group,
   specify its name as ``group_name:process_name``.

.. cmdoption:: -a, --any

   Send mail when any :command:`supervisord` child process transitions
   unexpectedly to the ``EXITED`` state.

   Overrides any ``-p`` parameters passed in the same :command:`crashmail`
   process invocation.

.. cmdoption:: -o <prefix>, --optionalheader=<prefix>

   Specify a parameter used as a prefix in the mail :mailheader:`Subject`
   header.

.. cmdoption:: -s <sendmail_command>, --sendmail_program=<sendmail_command>

   Specify the sendmail command to use to send email.

   Must be a command which accepts header and message data on stdin and
   sends mail.  Default is ``/usr/sbin/sendmail -t -i``.

.. cmdoption:: -m <email_address>, --email=<email_address>

   Specify an email address to which crash notification messages are sent.
   If no email address is specified, email will not be sent.


Configuring :command:`crashmail` Into the Supervisor Config
-----------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`crashmail` to do its work. See the "Events" chapter in
the Supervisor manual for more information about event listeners.

The following example assumes that :command:`crashmail` is on your system
:envvar:`PATH`.

.. code-block:: ini

   [eventlistener:crashmail]
   command=crashmail -p program1 -p group1:program2 -m dev@example.com
   events=PROCESS_STATE_EXITED
