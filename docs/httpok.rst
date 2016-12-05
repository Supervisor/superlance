:command:`httpok` Documentation
==================================

:command:`httpok` is a supervisor "event listener" which may be subscribed to
a concrete ``TICK_5``, ``TICK_60`` or ``TICK_3600``  event.
When :command:`httpok` receives a ``TICK_x``
event (``TICK_60`` is recommended, indicating activity every 60 seconds),
:command:`httpok` makes an HTTP GET request to a confgured URL. If the request
fails or times out, :command:`httpok` will restart the "hung" child
process(es). :command:`httpok` can be configured to send an email notification
when it restarts a process.

:command:`httpok` can only monitor the process status of processes
which are :command:`supervisord` child processes.

:command:`httpok` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`httpok` is an executable program, it
isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ httpok [-p processname] [-a] [-g] [-t timeout] [-c status_code] \
            [-b inbody] [-m mail_address] [-s sendmail] URL

.. program:: httpok

.. cmdoption:: -p <process_name>, --program=<process_name>

   Restart the :command:`supervisord` child process named ``process_name``
   if it is in the ``RUNNING`` state when the URL returns an unexpected
   result or times out.

   This option can be provided more than once to have :command:`httpok`
   monitor more than one process.

   To monitor a process which is part of a :command:`supervisord` group,
   specify its name as ``group_name:process_name``.

.. cmdoption:: -a, --any

   Restart any child of :command:`supervisord` in the ``RUNNING`` state
   if the URL returns an unexpected result or times out.

   Overrides any ``-p`` parameters passed in the same :command:`httpok`
   process invocation.

.. cmdoption:: -g <gcore_program>, --gcore=<gcore_program>

   Use the specifed program to ``gcore`` the :command:`supervisord` child
   process.  The program should accept two arguments on the command line:
   a filename and a pid.  Defaults to ``/usr/bin/gcore -o``.

.. cmdoption:: -d <core_directory>, --coredir=<core_directory>

   If a core directory is specified, :command:`httpok` will try to use the
   ``gcore`` program (see ``-g``) to write a core file into this directory
   for each hung process before restarting it.  It will then append any gcore
   stdout output to the email message, if mail is configured (see the ``-m``
   option below).

.. cmdoption:: -t <timeout>, --timeout=<timeout>

   The number of seconds that :command:`httpok` should wait for a response
   to the HTTP request before timing out.

   If this timeout is exceeded, :command:`httpok` will attempt to restart
   child processes which are in the ``RUNNING`` state, and specified by
   ``-p`` or ``-a``.

   Defaults to 10 seconds.

.. cmdoption:: -c <http_status_code>, --code=<http_status_code>

   Specify the expected HTTP status code for the configured URL.

   If this status code is not the status code provided by the response,
   :command:`httpok` will attempt to restart child processes which are
   in the ``RUNNING`` state, and specified by ``-p`` or ``-a``.

   Defaults to the string "200".

.. cmdoption:: -C <standard_stream>

   Specify 'stdout' or 'stderr' for generating PROCESS_COMMUNICATION
   events from httpok. This needs that the provided stream is placed
   in the 'capture mode' by setting std{err, out}_capture_maxbytes.

.. cmdoption:: -b <body_string>, --body=<body_string>

   Specify a string which should be present in the body resulting
   from the GET request.

   If this string is not present in the response, :command:`httpok` will
   attempt to restart child processes which are in the RUNNING state,
   and specified by ``-p`` or ``-a``.

   The default is to ignore the body.

.. cmdoption:: -B <body_restart_string>, --restart-string=<body_restart_string>

   Specify a string which should NOT be present in the body resulting
   from the GET request.

   If this string is present in the response, :command:`httpok` will
   attempt to restart child processes which are in the RUNNING state,
   and specified by ``-p`` or ``-a``. This option is the opposite of the -b
   option and can be specified multiple times and it may be specified along
   with the -b option.

   The default is to ignore the body.

.. cmdoption:: -s <sendmail_command>, --sendmail_program=<sendmail_command>

   Specify the sendmail command to use to send email.

   Must be a command which accepts header and message data on stdin and
   sends mail.  Default is ``/usr/sbin/sendmail -t -i``.

.. cmdoption:: -m <email_address>, --email=<email_address>

   Specify an email address to which notification messages are sent.
   If no email address is specified, email will not be sent.

.. cmdoption:: -e, --eager

   Enable "eager" monitoring:  check the URL and emit mail even if no
   monitored child process is in the ``RUNNING`` state.

   Enabled by default.

.. cmdoption:: -E, --not-eager

   Disable "eager" monitoring:  do not check the URL or emit mail if no
   monitored process is in the RUNNING state.

.. cmdoption:: -r, --restart-threshold

   Specify the maximum number of times program should be restarted if it
   does not return successful result while issuing a GET. 0 - for unlimited
   number of restarts. Default is 3.

.. cmdoption:: -n, --restart-timespan

   Specify the time span in minutes during which the maximum number of
   restarts could happen. This prevents loop restarts when the application
   is running fine for configured TICK seconds then starts to fail again.
   Default is 60.

.. cmdoption:: -x --external-service-script

   Optionally specify an external script to restart the program, e.g.
   /etc/init.d/myprogramservicescript.

.. cmdoption:: -G --grace-period

   Specify the grace period in minutes before starting to act on programs
   which are failing their healthchecks. Grace period is counted since
   the last time program was (re)started.

.. cmdoption:: -o --grace-count

   Specify the grace count to ignore a number of errors before
   restarting programs which are failing their healthchecks. Grace count
   is counted since the last time program was (re)started and is checked
   before program restart counter (-n option). Default is 0.

.. cmdoption:: URL

   The URL to which to issue a GET request.


Configuring :command:`httpok` Into the Supervisor Config
-----------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`httpok` to do its work.
See the "Events" chapter in the
Supervisor manual for more information about event listeners.

The following examples assume that :command:`httpok` is on your system
:envvar:`PATH`.

.. code-block:: ini

   [eventlistener:httpok]
   command=httpok -p program1 -p group1:program2 http://localhost:8080/tasty
   events=TICK_60

.. code-block:: ini

   [eventlistener:httpok]
   command=httpok -p program1 -r 3 -n 60 http://localhost:8080/tasty
   events=TICK_60
