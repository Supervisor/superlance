:command:`crashsms` Documentation
==================================

:command:`crashsms` is a supervisor "event listener", intended to be
subscribed to ``PROCESS_STATE`` events and ``TICK`` events such as ``TICK_60``.  It monitors
all processes running under a given supervisord instance.

Similar to :command:`crashmailbatch`, :command:`crashsms` sends SMS alerts
through an email gateway.  Messages are formatted to fit in SMS

:command:`crashsms` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`crashsms` is an executable 
program, it isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ crashsms --toEmail=<email address> --fromEmail=<email address> \
           [--interval=<batch interval in minutes>] [--subject=<email subject>] \
		   [--tickEvent=<event name>]
   
.. program:: crashsms

.. cmdoption:: -t <destination email>, --toEmail=<destination email>
   
   Specify an email address to which crash notification messages are sent.
 
.. cmdoption:: -f <source email>, --fromEmail=<source email>
   
   Specify an email address from which crash notification messages are sent.

.. cmdoption:: -i <interval>, --interval=<interval>
   
   Specify the time interval in minutes to use for batching notifcations.
   Defaults to 1.0 minute.

.. cmdoption:: -s <email subject>, --subject=<email subject>
   
   Set the email subject line.  Default is None

.. cmdoption:: -e <event name>, --tickEvent=<event name>

   Override the TICK event name.  Defaults to "TICK_60"

Configuring :command:`crashsms` Into the Supervisor Config
-----------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`crashsms` to do its work. See the "Events" chapter in
the Supervisor manual for more information about event listeners.

The following example assumes that :command:`crashsms` is on your system
:envvar:`PATH`.

.. code-block:: ini

   [eventlistener:crashsms]
   command=crashsms --toEmail="<mobile number>@<sms email gateway>" --fromEmail="supervisord@fubar.com" 
   events=PROCESS_STATE,TICK_60
