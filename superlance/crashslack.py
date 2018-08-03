doc = """\
crashslack.py [-p processname] [-a] [-c slack_channel]
             [-t slack_token] URL

Options:

-p -- specify a supervisor process_name.  Send mail when this process
      transitions to the EXITED state unexpectedly. If this process is
      part of a group, it can be specified using the
      'group_name:process_name' syntax.

-a -- Send Slack message when any child of the supervisord transitions
      unexpectedly to the EXITED state unexpectedly.  Overrides any -p
      parameters passed in the same crashmail process invocation.

-c -- specify a slack channel t publish to. The script will send a message
      to this channel when crashslack detetcs a process crash. If no channel
      is specified, notification will not be sent.

-t -- specify a Slack authentication token. The script will use this token to
      authorize message psoting requests to the specified channel. If no token
      is specified, notification will not be sent.

The -p option may be specified more than once, allowing for
specification of multiple processes.  Specifying -a overrides any
selection of -p.

A sample invocation:

crashslack.py -p program1 -p group1:program2 -c C0XXXXXX -t xoxp-xxxxxxxxxxx-xxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxx

"""

import getopt
import os
import sys

from supervisor import childutils
from slackclient import SlackClient


def usage(exitstatus=255):
    print(doc)
    sys.exit(exitstatus)
    
    
class CrashSlack:

    def __init__(self, programs, any, channel, token):

        self.programs = programs
        self.any = any
        self.channel = channel
        self.slack_client = SlackClient(token)
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

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

            msg = ('Process %(processname)s in group %(groupname)s exited '
                   'unexpectedly (pid %(pid)s) from state %(from_state)s' %
                   pheaders)

            subject = ' %s crashed at %s' % (pheaders['processname'],
                                             childutils.get_asctime())
            

            self.stderr.write('unexpected exit, posting to Slack\n')
            self.stderr.flush()

            self.slack(self.channel, subject, msg)

            childutils.listener.ok(self.stdout)
            if test:
                break


    def slack(self, channel, subject, msg):
        attach_json = [
            {
                "text": subject,
                "color": "danger"
            }
        ]
        self.slackclient.api_call(
            "chat.postMessage",
            username="Supervisor",
            channel=channel,
            text=msg,
            attachments=attach_json
        )


    def main(argv=sys.argv):
        short_args = "hp:a:t:c:"
        long_args = [
            "help",
            "program=",
            "any",
            "token=",
            "channel=",
            ]
        arguments = argv[1:]
        try:
            opts, args = getopt.getopt(arguments, short_args, long_args)
        except:
            usage()

        programs = []
        any = False
        channel = None

        for option, value in opts:

            if option in ('-h', '--help'):
                usage(exitstatus=0)

            if option in ('-p', '--program'):
                programs.append(value)

            if option in ('-a', '--any'):
                any = True

            if option in ('-c', '--channel'):
                channel = value

            if option in ('-t', '--token'):
                token = value

        if not 'SUPERVISOR_SERVER_URL' in os.environ:
            sys.stderr.write('crashslack must be run as a supervisor event '
                            'listener\n')
            sys.stderr.flush()
            return

        prog = CrashSlack(programs, any, channel, token)
        prog.runforever()


if __name__ == '__main__':
    main()
