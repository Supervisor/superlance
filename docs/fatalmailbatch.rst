:command:`fatalmailbatch` Documentation
=======================================

:command:`fatalmailbatch` is a supervisor "event listener", intended to be
subscribed to ``PROCESS_STATE`` and ``TICK_60`` events.  It monitors
all processes running under a given supervisord instance.

:command:`fatalmailbatch` sends email alerts when processes fail to start 
too many times such that supervisord gives up retrying.  All of the fatal
start events generated within the configured time interval are batched 
together to avoid sending too many emails.   

:command:`fatalmailbatch` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`fatalmailbatch` is an executable 
program, it isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ fatalmailbatch --toEmail=<email address> --fromEmail=<email address> \
           [--interval=<batch interval in minutes>] [--subject=<email subject>]
   
.. program:: fatalmailbatch

.. cmdoption:: -t <destination email>, --toEmail=<destination email>
   
   Specify an email address to which fatal start notification messages are sent.
 
.. cmdoption:: -f <source email>, --fromEmail=<source email>
   
   Specify an email address from which fatal start notification messages 
   are sent.

.. cmdoption:: -i <interval>, --interval=<interval>
   
   Specify the time interval in minutes to use for batching notifcations.
   Defaults to 1 minute.

.. cmdoption:: -s <email subject>, --subject=<email subject>
   
   Override the email subject line.  Defaults to "Fatal start alert from 
   supervisord"

Configuring :command:`fatalmailbatch` Into the Supervisor Config
----------------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`fatalmailbatch` to do its work. See the "Events" chapter in
the Supervisor manual for more information about event listeners.

The following example assumes that :command:`fatalmailbatch` is on your system
:envvar:`PATH`.

.. code-block:: ini

   [eventlistener:fatalmailbatch]
   command=fatalmailbatch --toEmail="alertme@fubar.com" --fromEmail="supervisord@fubar.com" 
   events=PROCESS_STATE,TICK_60
