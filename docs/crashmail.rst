:command:`crashmail` Documentation
==================================

Command-Line Syntax
-------------------

.. program:: crashmail

.. cmdoption:: -p <process_name>
   
   Send mail when the specified :command:`supervisord` child process
   transitions unexpectedly to the ``EXITED`` state.

   This option may be specified more than once, allowing for specification
   of multiple processes.
   
   To monitor a process which is part of a :command:`supervisord` group,
   specify its name as ``process_name:group_name``.
 
.. cmdoption:: -a
   
   Send mail when any :command:`supervisord` child process transitions
   unexpectedly to the ``EXITED`` state.
   
   Overrides any ``-p`` parameters passed in the same :command:`crashmail`
   process invocation.

.. cmdoption:: -o
   
   Specify a parameter used as a prefix in the mail :mailheader:`Subject`
   header.

.. cmdoption:: -s
   
   Specify the sendmail command to use to send email.
   
   Must be a command which accepts header and message data on stdin and
   sends mail.  Default is ``/usr/sbin/sendmail -t -i``.

.. cmdoption:: -m
   
   Specify an email address to which crash notification messages are sent.
   If no email address is specified, email will not be sent.


Configuring :command:`crashmail` Into the Supervisor Config
-----------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`memmon` to do its work. See the "Events" chapter in the
Supervisor manual for more information about event listeners.

The following example assumes that :command:`crashmail` is on your system
:envvar:`PATH`.

.. code-block:: ini

   [eventlistener:crashmail]
   crashmail.py -p program1 -p group1:program2 -m dev@example.com
   events=PROCESS_STATE_EXITED
