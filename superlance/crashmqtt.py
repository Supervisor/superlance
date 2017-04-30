#!/usr/bin/env python
#
# Based on https://github.com/Supervisor/superlance/blob/master/superlance/crashmail.py
#
# A event listener meant to be subscribed to PROCESS_STATE_CHANGE
# events.  It will publish an MQTT message when processes that are children of
# supervisord transition unexpectedly to the EXITED state.

# A supervisor config snippet that tells supervisor to use this script
# as a listener is below.
#
# [eventlistener:crashmqtt]
# command =
#     /usr/bin/crashmqtt
#         -p program -a
#         -h mqttbroker -o mqttport
#         -u mqttuser -P mqttpwd
#         -t mqtttopic
#         -m mqttmessage
#
# events=PROCESS_STATE
#

doc = """\ crashmqtt.py [-p processname] [-a]
             [-b mqttbroker] [-o mqttport] [-u mqttuser] [-P mqttpwd]
             [-t mqtttopic]
Options:
-p -- specify a supervisor process_name.  Publish MQTT when this process
      transitions to the EXITED state unexpectedly. If this process is
      part of a group, it can be specified using the
      'process_name:group_name' syntax.
-a -- Publish MQTT when any child of the supervisord transitions
      unexpectedly to the EXITED state unexpectedly.  Overrides any -p
      parameters passed in the same crashmqtt process invocation.
-b -- MQTT broker address. Defaults to localhost.
-o -- MQTT broker port. Defaults to 1883.
-u -- MQTT broker user.
-P -- MQTT broker password.
-t -- MQTT topic to publish to. Will substitute event details in topic string.
-m -- MQTT message to publish. Will substitute event details in message string.
The -p option may be specified more than once, allowing for
specification of multiple processes.  Specifying -a overrides any
selection of -p.
A sample invocation:
crashmqtt.py -p program1 -p group1:program2 -t monitor/{processname} -m 'terminated'
"""

import paho.mqtt.publish as mqtt
import os
import sys

from supervisor import childutils


def usage():
    print(doc)
    sys.exit(255)


class CrashMqtt:

    def __init__(self, programs, any,
                 mqttbroker, mqttport, mqttuser, mqttpwd,
                 mqtttopic, mqttmsg):

        self.programs   = programs
        self.any        = any
        self.mqttbroker = mqttbroker
        self.mqttport   = mqttport
        self.mqttuser   = mqttuser
        self.mqttpwd    = mqttpwd
        self.mqtttopic  = mqtttopic
        self.mqttmsg    = mqttmsg
        self.stdin      = sys.stdin
        self.stdout     = sys.stdout
        self.stderr     = sys.stderr

        self.mqttclient = "crashmqtt"
        self.mqttqos    = 0
        self.mqttretain = False

    def runforever(self, test=False):
        while 1:
            # we explicitly use self.stdin, self.stdout, and self.stderr
            # instead of sys.* so we can unit test this code
            headers, payload = childutils.listener.wait(
                self.stdin, self.stdout)

            if not headers['eventname'] == 'PROCESS_STATE_EXITED':
                # do nothing with non-TICK events
                childutils.listener.ok(self.stdout)
                if test:
                    self.stderr.write('non-exited event\n')
                    self.stderr.flush()
                    break
                continue

            pheaders, pdata = childutils.eventdata(payload+'\n')

            if int(pheaders['expected']):
                childutils.listener.ok(self.stdout)
                if test:
                    self.stderr.write('expected exit\n')
                    self.stderr.flush()
                    break
                continue

            topic = self.mqtttopic.format(**pheaders)
            msg   = self.mqttmsg.format(**pheaders)

            self.stderr.write('unexpected exit, publishing MQTT\n')
            self.stderr.flush()

            self.mqtt_pub(topic, msg)

            childutils.listener.ok(self.stdout)
            if test:
                break

    def mqtt_pub(self, topic, msg):
        params = {
            'hostname'  : self.mqttbroker,
            'port'      : self.mqttport,
            'client_id' : self.mqttclient,
            'qos'       : self.mqttqos,
            'retain'    : self.mqttretain,
        }

        auth = None
        tls = None

        if self.mqttuser is not None:
            auth = {
                'username' : self.mqttuser,
                'password' : self.mqttpwd
            }

        self.stderr.write('publishing \'%s\' to [%s:%d]%s...' %
            (msg, self.mqttbroker, self.mqttport, topic))

        mqtt.single(topic, msg, auth=auth, tls=tls, **params)

        self.stderr.write('success\n')
        self.stderr.flush()

def main(argv=sys.argv):
    import getopt
    short_args = "hp:ab:o:u:P:t:m:"
    long_args = [
        "help",
        "program=",
        "any",
        "mqtt_broker=",
        "mqtt_port=",
        "mqtt_user=",
        "mqtt_pwd=",
        "mqtt_topic=",
        "mqtt_msg=",
        ]
    arguments = argv[1:]
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        usage()

    programs   = []
    any        = False
    mqttbroker = "localhost"
    mqttport   = 1883
    mqttuser   = None
    mqttpwd    = None
    mqttmsg    = "0"

    for option, value in opts:

        if option in ('-h', '--help'):
            usage()

        if option in ('-p', '--program'):
            programs.append(value)

        if option in ('-a', '--any'):
            any = True

        if option in ('-b', '--mqtt_broker'):
            mqttbroker = value

        if option in ('-o', '--mqtt_port'):
            mqttport = int(value)

        if option in ('-u', '--mqtt_user'):
            mqttuser = value

        if option in ('-P', '--mqtt_pwd'):
            mqttpwd = value

        if option in ('-t', '--mqtt_topic'):
            mqtttopic = value

        if option in ('-m', '--mqtt_msg'):
            mqttmsg = value

    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        sys.stderr.write('crashmqtt must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return

    prog = CrashMqtt(programs, any,
                     mqttbroker, mqttport, mqttuser, mqttpwd,
                     mqtttopic, mqttmsg)
    prog.runforever()


if __name__ == '__main__':
    main()
