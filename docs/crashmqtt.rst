:command:`crashmqtt` Documentation
==================================

:command:`crashmqtt` is a supervisor "event listener", intended to be
subscribed to ``PROCESS_STATE_EXITED`` events. When :command:`crashmqtt`
receives that event, and the transition is "unexpected", :command:`crashmqtt``
publishes an MQTT message to a configured MQTT broker..

:command:`crashmqtt` is incapable of monitoring the process status of processes
which are not :command:`supervisord` child processes.

:command:`crashmqtt` is a "console script" installed when you install
:mod:`superlance`.  Although :command:`crashmqtt` is an executable program, it
isn't useful as a general-purpose script:  it must be run as a
:command:`supervisor` event listener to do anything useful.

Command-Line Syntax
-------------------

.. code-block:: sh

   $ crashmqtt [-p processname] [-a] [-b mqttbroker] [-o mqttport] \
               [-u mqttuser] [-P mqttpwd] \
               [-t mqtttopic] [-m mqttmsg]

.. program:: crashmqtt

.. cmdoption:: -p <process_name>, --program=<process_name>

   Publish MQTT when the specified :command:`supervisord` child process
   transitions unexpectedly to the ``EXITED`` state.

   This option can be provided more than once to have :command:`crashmqtt`
   monitor more than one program.

   To monitor a process which is part of a :command:`supervisord` group,
   specify its name as ``process_name:group_name``.

.. cmdoption:: -a, --any

   Publish MQTT when any :command:`supervisord` child process transitions
   unexpectedly to the ``EXITED`` state.

   Overrides any ``-p`` parameters passed in the same :command:`crashmqtt`
   process invocation.

.. cmdoption:: -b <mqttbroker>, --mqtt_broker=<mqttbroker>

   Specify the MQTT broker host name. Defaults to 'localhost'.

.. cmdoption:: -o <mqttport>, --mqtt_port=<mqttport>

   Specify the MQTT broker port. Defaults to 1883.

.. cmdoption:: -u <mqttuser>, --mqtt_user=<mqttuser>

   Specify the MQTT broker user name for authentication. Optional.

.. cmdoption:: -P <mqttpwd>, --mqtt_pwd=<mqttpwd>

   Specify the MQTT broker password for authentication. Optional.

.. cmdoption:: -t <mqtttopic>, --mqtt_topic=<mqtttopic>

   Specify the MQTT topic to publish to. Supports substitution of values
   in the PROCESS_STATE_EXITED event. For example 'network/alert/{processname}'.

.. cmdoption:: -m <mqttmsg>, --mqtt_msg=<mqttmsg>

   Specify the MQTT message to publish. Supports substitution of values
   in the PROCESS_STATE_EXITED event. For example '{processname} terminated'.


Configuring :command:`crashmqtt` Into the Supervisor Config
-----------------------------------------------------------

An ``[eventlistener:x]`` section must be placed in :file:`supervisord.conf`
in order for :command:`crashmqtt` to do its work. See the "Events" chapter in
the Supervisor manual for more information about event listeners.

The following example assumes that :command:`crashmqtt` is on your system
:envvar:`PATH`.

.. code-block:: ini

   [eventlistener:crashmqtt]
   command=crashmqtt -p program1 -p group1:program2 -t network/alert -m '{processname} terminated'
   events=PROCESS_STATE_EXITED
