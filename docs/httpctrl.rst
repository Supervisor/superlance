:command:`httpctrl` Documentation
==================================

:command:`httpctrl` is a supervisor "event listener" which may be subscribed to
a concrete ``TICK_x`` event. When :command:`httpctrl` receives a ``TICK_x``
event (``TICK_5`` is recommended, indicating activity every 5 seconds),
:command:`httctrl` makes an HTTP GET request to a confgured URL. If the response 
body contains required text :command:`httpctrl` will start child process(es).
If the response body does not contain required text :command:`httpctrl` will
stop child process(es).

:command:`httpctrl` is incapable of monitoring the process status of processes
which are not :command:`supervisord` child processes.

:command:`httpctrl` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`httpctrl` is an executable program, it
isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ httpctrl [-p processname] [-a] [-b inbody] URL

.. program:: httpctrl

.. cmdoption:: -p <process_name>, --program=<process_name>

   Specify a supervisor 'process_name' or 'group_name'.

   Starts the supervisor process if it's in STOPPED state and specified
   string is present in body of URL.

   Stops the supervisor process if it's in the RUNNING state when
   specified string is not present in the body of URL.

   If this process is part of a group, it can be specified using
   the 'group_name:process_name' syntax.

.. cmdoption:: -b <body_string>, --body=<body_string>

   Specify a string which should be present in the body resulting
   from the GET request. 
   
   If this string is not present in the response, the processes in 
   the RUNNING state specified by -p will be stopped in another 
   case it will be started.

.. cmdoption:: <URL>
   
   The URL to which to issue a GET request.


Configuring :command:`httpctrl` Into the Supervisor Config
-----------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`memmon` to do its work. See the "Events" chapter in the
Supervisor manual for more information about event listeners.

The following example assumes that :command:`httpctrl` is on your system
:envvar:`PATH`.

.. code-block:: ini

   [eventlistener:httpctrl]
   httpctrl.py -p program1 -p group1:program2 -p group2 http://localhost:8080/tasty
   events=TICK_5
