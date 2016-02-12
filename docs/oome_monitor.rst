:command:`oome_monitor` Documentation
=====================================

:command:`oome_monitor` is a supervisor "event listener" which may be
subscribed to a concrete ``TICK_5``, ``TICK_60`` or ``TICK_3600``  event.
When :command:`oome_monitor` receives a ``TICK_x`` event (``TICK_60`` is
recommended, indicating activity every 60 seconds), :command:`oome_monitor`
restarts processes that are children of supervisord based on the out-of-memory
error conditions (described below). :command:`oome_monitor` will monitor
specified directory for a ".oome" file and restart the processes accordingly.

Example usage of :command:`oome_monitor` is to manage a tomcat instance which
creates an ".oome" file when out of memory conditions are met, e.g.:
-XX:OnOutOfMemoryError="touch /tmp/tomcat.oome"

:command:`oome_monitor` will try to guess ".oome" absolute file path based on
the following:
* If its provided as an argument - use that
* $OOME_FILE environment variable of the process
* $CWD of the process + /work/oome
  
:command:`oome_monitor` could be run to monitor all supervisord processes or
specified ones inside the configuration file. In case if only one process is
monitored it is possible to provide an absolute path of the oome file.

:command:`oome_monitor` can only monitor the process status of processes
which are :command:`supervisord` child processes.

:command:`oome_monitor` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`oome_monitor` is an executable program, it
isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ oome_monitor [-h] single

.. program:: oome_monitor

.. option:: -p <process_name>, --process-name=<process_name>

   Restart the :command:`supervisord` child process named ``process_name``
   if there's a ".oome" file in configured path.

   This option can be provided more than once to have :command:`oome_monitor`
   monitor more than one process.

.. option:: -o <oome_file>, --oome-file <oome_file>

   For single process optionally provide an oome file name ``oome_file``

.. code-block:: sh

   $ oome_monitor [-h] single|all

.. program:: oome_monitor

.. option:: -d, --dry

   Do not actually kill or restart the procesesses, only log the actions.

.. option:: -h, --help

   Display help information.


Configuring :command:`oome_monitor` Into the Supervisor Config
--------------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`oome_monitor` to do its work.
See the "Events" chapter in the
Supervisor manual for more information about event listeners.

The following examples assumes that :command:`oome_monitor` is on your system
:envvar:`PATH`.

.. code-block:: ini

   # To configure all supervisord daemons
   [eventlistener:oome_listener]
   command=oome_monitor all
   events=TICK_60

   # To configure specific applications to be monitored
   [eventlistener:oome_listener]
   command=oome_monitor single -p webapp1 -p webapp2
   events=TICK_5

   # To configure one app with specific oome file
   [eventlistener:oome_listener]
   command=oome_monitor single -p webapp -o /tmp/webapp.oome
   events=TICK_60

   # Dry run / test mode
   [eventlistener:oome_listener]
   command=oome_monitor all -d
   events=TICK_5