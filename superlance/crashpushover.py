#!/usr/bin/env python -u
##############################################################################
#
# Copyright (c) 2007 Agendaless Consulting and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE
#
##############################################################################

# A event listener meant to be subscribed to PROCESS_STATE_CHANGE
# events.  It will send push notifications when processes that are children of
# supervisord transition unexpectedly to the EXITED state.

# A supervisor config snippet that tells supervisor to use this script
# as a listener is below.
#
# [eventlistener:crashpushover]
# command=/usr/bin/crashpushover -a -m 1234567890 -a 1234567890
# events=PROCESS_STATE
#

doc = """\
crashpushover.py [-p processname] [-a] [-t string] [-m string]

Options:

-p -- specify a supervisor process_name.  Send mail when this process
      transitions to the EXITED state unexpectedly. If this process is
      part of a group, it can be specified using the
      'process_name:group_name' syntax.

-t -- application id

-m -- client id

The -p option may be specified more than once, allowing for
specification of multiple processes.  Specifying -a overrides any
selection of -p.

A sample invocation:

crashpushover.py -p program1 -p group1:program2 -t 1234567890 -m 1234567890

"""

import os
import sys
import pushover

from supervisor import childutils

def usage():
    print doc
    sys.exit(255)

class crashpushover:

    def __init__(self, programs, any, user, token):

        self.programs = programs
        self.any = any
        self.user = user
        self.token = token
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def runforever(self, test=False):
        while 1:
            # we explicitly use self.stdin, self.stdout, and self.stderr
            # instead of sys.* so we can unit test this code
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)

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

            subject = '%s crashed at %s' % (pheaders['processname'],
                                             childutils.get_asctime())

            self.stderr.write('unexpected exit, mailing\n')
            self.stderr.flush()

            self.pushit(self.user, self.token, subject, msg)

            childutils.listener.ok(self.stdout)
            if test:
                break

    def pushit(self, client_id, token, subject, msg):
        body = 'Subject: %s\n' % subject
        body += '\n'
        body += msg

        pushover.init(token);
        client = pushover.Client(client_id);
        client.send_message(msg, title=subject, priority=1)

        self.stderr.write('Mailed:\n\n%s' % body)
        self.mailed = body

def main(argv=sys.argv):
    import getopt
    short_args="hp:am:t:"
    long_args=[
        "help",
        "program=",
        "any",
        "user:"
        "token:",
        ]
    arguments = argv[1:]
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        usage()

    programs = []
    any = False
    token = None
    user = None
    timeout = 10
    status = '200'

    for option, value in opts:

        if option in ('-h', '--help'):
            usage()

        if option in ('-p', '--program'):
            programs.append(value)

        if option in ('-a', '--any'):
            any = True

        if option in ('-t', '--token'):
            token = value

        if option in ('-m', '--user'):
            user = value

    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        sys.stderr.write('crashpushover must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return

    prog = crashpushover(programs, any, user, token)
    prog.runforever()

if __name__ == '__main__':
    main()

