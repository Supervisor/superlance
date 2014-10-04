:command:`crashmailbatch` Documentation
=======================================

:command:`crashmailbatch` is a supervisor "event listener", intended to be
subscribed to ``PROCESS_STATE`` and ``TICK_60`` events.  It monitors
all processes running under a given supervisord instance.

Similar to :command:`crashmail`, :command:`crashmailbatch` sends email 
alerts when processes die unexpectedly.  The difference is that all alerts 
generated within the configured time interval are batched together to avoid 
sending too many emails.   

:command:`crashmailbatch` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`crashmailbatch` is an executable 
program, it isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ crashmailbatch --toEmail=<email address> --fromEmail=<email address> \
           [--interval=<batch interval in minutes>] [--subject=<email subject>] \
		   [--tickEvent=<event name>]
   
.. program:: crashmailbatch

.. cmdoption:: -t <destination email>, --toEmail=<destination email>
   
   Specify an email address to which crash notification messages are sent.
 
.. cmdoption:: -f <source email>, --fromEmail=<source email>
   
   Specify an email address from which crash notification messages are sent.

.. cmdoption:: -i <interval>, --interval=<interval>
   
   Specify the time interval in minutes to use for batching notifcations.
   Defaults to 1.0 minute.

.. cmdoption:: -s <email subject>, --subject=<email subject>
   
   Override the email subject line.  Defaults to "Crash alert from supervisord"

.. cmdoption:: -e <event name>, --tickEvent=<event name>

   Override the TICK event name.  Defaults to "TICK_60"

Configuring :command:`crashmailbatch` Into the Supervisor Config
----------------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`crashmailbatch` to do its work. See the "Events" chapter in
the Supervisor manual for more information about event listeners.

The following example assumes that :command:`crashmailbatch` is on your system
:envvar:`PATH`.

.. code-block:: ini

   [eventlistener:crashmailbatch]
   command=crashmailbatch --toEmail="alertme@fubar.com" --fromEmail="supervisord@fubar.com" 
   events=PROCESS_STATE,TICK_60
