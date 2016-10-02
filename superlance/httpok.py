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

# A event listener meant to be subscribed to TICK_60 (or TICK_5)
# events, which restarts processes that are children of
# supervisord based on the response from an HTTP port.

# A supervisor config snippet that tells supervisor to use this script
# as a listener is below.
#
# [eventlistener:httpok]
# command=python -u /bin/httpok http://localhost:8080/tasty/service
# events=TICK_60

doc = """\
httpok.py [-p processname] [-a] [-g] [-t timeout] [-c status_code] [-b inbody]
          [-m mail_address] [-s sendmail] URL

Options:

-p -- specify a supervisor process_name.  Restart the supervisor
      process named 'process_name' if it's in the RUNNING state when
      the URL returns an unexpected result or times out.  If this
      process is part of a group, it can be specified using the
      'group_name:process_name' syntax.

-a -- Restart any child of the supervisord under in the RUNNING state
      if the URL returns an unexpected result or times out.  Overrides
      any -p parameters passed in the same httpok process
      invocation.

-g -- The ``gcore`` program.  By default, this is ``/usr/bin/gcore
      -o``.  The program should accept two arguments on the command
      line: a filename and a pid.

-d -- Core directory.  If a core directory is specified, httpok will
      try to use the ``gcore`` program (see ``-g``) to write a core
      file into this directory against each hung process before we
      restart it.  Append gcore stdout output to email.

-t -- The number of seconds that httpok should wait for a response
      before timing out.  If this timeout is exceeded, httpok will
      attempt to restart processes in the RUNNING state specified by
      -p or -a.  This defaults to 10 seconds.

-c -- specify an expected HTTP status code from a GET request to the
      URL.  If this status code is not the status code provided by the
      response, httpok will attempt to restart processes in the
      RUNNING state specified by -p or -a.  Default is 200.

-b -- specify a string which should be present in the body resulting
      from the GET request.  If this string is not present in the
      response, the processes in the RUNNING state specified by -p
      or -a will be restarted.  The default is to ignore the
      body.

-s -- the sendmail command to use to send email
      (e.g. "/usr/sbin/sendmail -t -i").  Must be a command which accepts
      header and message data on stdin and sends mail.
      Default is "/usr/sbin/sendmail -t -i".

-m -- specify an email address.  The script will send mail to this
      address when httpok attempts to restart processes.  If no email
      address is specified, email will not be sent.

-e -- "eager":  check URL / emit mail even if no process we are monitoring
      is in the RUNNING state.  Enabled by default.

-E -- not "eager":  do not check URL / emit mail if no process we are
      monitoring is in the RUNNING state.

-n -- optionally specify the name of the httpok process.  This name will
      be used in the email subject to identify which httpok process
      restarted the process.

URL -- The URL to which to issue a GET request.

The -c option may be specified more than once, allowing for
specification of multiple expected HTTP status codes.

The -p option may be specified more than once, allowing for
specification of multiple processes.  Specifying -a overrides any
selection of -p.

A sample invocation:

httpok.py -p program1 -p group1:program2 http://localhost:8080/tasty

"""

import getopt
import os
import socket
import sys
import time
from superlance.compat import urlparse
from superlance.compat import xmlrpclib

from supervisor import childutils
from supervisor.states import ProcessStates
from supervisor.options import make_namespec

from superlance import timeoutconn

def usage(exitstatus=255):
    print(doc)
    sys.exit(exitstatus)

class HTTPOk:
    connclass = None
    def __init__(self, rpc, programs, any, url, timeout, statuses, inbody,
                 email, sendmail, coredir, gcore, eager, retry_time, name):
        self.rpc = rpc
        self.programs = programs
        self.any = any
        self.url = url
        self.timeout = timeout
        self.retry_time = retry_time
        self.statuses = statuses
        self.inbody = inbody
        self.email = email
        self.sendmail = sendmail
        self.coredir = coredir
        self.gcore = gcore
        self.eager = eager
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.name = name

    def listProcesses(self, state=None):
        return [x for x in self.rpc.supervisor.getAllProcessInfo()
                   if x['name'] in self.programs and
                      (state is None or x['state'] == state)]

    def runforever(self, test=False):
        parsed = urlparse.urlsplit(self.url)
        scheme = parsed.scheme.lower()
        hostport = parsed.netloc
        path = parsed.path
        query = parsed.query

        if query:
            path += '?' + query

        if self.connclass:
            ConnClass = self.connclass
        elif scheme == 'http':
            ConnClass = timeoutconn.TimeoutHTTPConnection
        elif scheme == 'https':
            ConnClass = timeoutconn.TimeoutHTTPSConnection
        else:
            raise ValueError('Bad scheme %s' % scheme)

        while 1:
            # we explicitly use self.stdin, self.stdout, and self.stderr
            # instead of sys.* so we can unit test this code
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)

            if not headers['eventname'].startswith('TICK'):
                # do nothing with non-TICK events
                childutils.listener.ok(self.stdout)
                if test:
                    break
                continue

            conn = ConnClass(hostport)
            conn.timeout = self.timeout

            specs = self.listProcesses(ProcessStates.RUNNING)
            if self.eager or len(specs) > 0:

                try:
                    for will_retry in range(
                            self.timeout // (self.retry_time or 1) - 1 ,
                            -1, -1):
                        try:
                            headers = {'User-Agent': 'httpok'}
                            conn.request('GET', path, headers=headers)
                            break
                        except socket.error as e:
                            if e.errno == 111 and will_retry:
                                time.sleep(self.retry_time)
                            else:
                                raise

                    res = conn.getresponse()
                    body = res.read()
                    status = res.status
                    msg = 'status contacting %s: %s %s' % (self.url,
                                                           res.status,
                                                           res.reason)
                except Exception as e:
                    body = ''
                    status = None
                    msg = 'error contacting %s:\n\n %s' % (self.url, e)

                if status not in self.statuses:
                    subject = self.format_subject(
                        '%s: bad status returned' % self.url
                        )
                    self.act(subject, msg)
                elif self.inbody and self.inbody not in body:
                    subject = self.format_subject(
                        '%s: bad body returned' % self.url
                    )
                    self.act(subject, msg)

            childutils.listener.ok(self.stdout)
            if test:
                break

    def format_subject(self, subject):
        if self.name is None:
            return 'httpok: %s' % subject
        else:
            return 'httpok [%s]: %s' % (self.name, subject)

    def act(self, subject, msg):
        messages = [msg]

        def write(msg):
            self.stderr.write('%s\n' % msg)
            self.stderr.flush()
            messages.append(msg)

        try:
            specs = self.rpc.supervisor.getAllProcessInfo()
        except Exception as e:
            write('Exception retrieving process info %s, not acting' % e)
            return

        waiting = list(self.programs)

        if self.any:
            write('Restarting all running processes')
            for spec in specs:
                name = spec['name']
                group = spec['group']
                self.restart(spec, write)
                namespec = make_namespec(group, name)
                if name in waiting:
                    waiting.remove(name)
                if namespec in waiting:
                    waiting.remove(namespec)
        else:
            write('Restarting selected processes %s' % self.programs)
            for spec in specs:
                name = spec['name']
                group = spec['group']
                namespec = make_namespec(group, name)
                if (name in self.programs) or (namespec in self.programs):
                    self.restart(spec, write)
                    if name in waiting:
                        waiting.remove(name)
                    if namespec in waiting:
                        waiting.remove(namespec)

        if waiting:
            write(
                'Programs not restarted because they did not exist: %s' %
                waiting)

        if self.email:
            message = '\n'.join(messages)
            self.mail(self.email, subject, message)

    def mail(self, email, subject, msg):
        body =  'To: %s\n' % self.email
        body += 'Subject: %s\n' % subject
        body += '\n'
        body += msg
        with os.popen(self.sendmail, 'w') as m:
            m.write(body)
        self.stderr.write('Mailed:\n\n%s' % body)
        self.mailed = body

    def restart(self, spec, write):
        namespec = make_namespec(spec['group'], spec['name'])
        if spec['state'] is ProcessStates.RUNNING:
            if self.coredir and self.gcore:
                corename = os.path.join(self.coredir, namespec)
                cmd = self.gcore + ' "%s" %s' % (corename, spec['pid'])
                with os.popen(cmd) as m:
                    write('gcore output for %s:\n\n %s' % (
                        namespec, m.read()))
            write('%s is in RUNNING state, restarting' % namespec)
            try:
                self.rpc.supervisor.stopProcess(namespec)
            except xmlrpclib.Fault as e:
                write('Failed to stop process %s: %s' % (
                    namespec, e))

            try:
                self.rpc.supervisor.startProcess(namespec)
            except xmlrpclib.Fault as e:
                write('Failed to start process %s: %s' % (
                    namespec, e))
            else:
                write('%s restarted' % namespec)

        else:
            write('%s not in RUNNING state, NOT restarting' % namespec)


def main(argv=sys.argv):
    short_args="hp:at:c:b:s:m:g:d:eEn:"
    long_args=[
        "help",
        "program=",
        "any",
        "timeout=",
        "code=",
        "body=",
        "sendmail_program=",
        "email=",
        "gcore=",
        "coredir=",
        "eager",
        "not-eager",
        "name=",
        ]
    arguments = argv[1:]
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        usage()

    # check for -h must be done before positional args check
    for option, value in opts:
        if option in ('-h', '--help'):
            usage(exitstatus=0)

    if not args:
        usage()
    if len(args) > 1:
        usage()

    programs = []
    any = False
    sendmail = '/usr/sbin/sendmail -t -i'
    gcore = '/usr/bin/gcore -o'
    coredir = None
    eager = True
    email = None
    timeout = 10
    retry_time = 10
    statuses = []
    inbody = None
    name = None

    for option, value in opts:

        if option in ('-p', '--program'):
            programs.append(value)

        if option in ('-a', '--any'):
            any = True

        if option in ('-s', '--sendmail_program'):
            sendmail = value

        if option in ('-m', '--email'):
            email = value

        if option in ('-t', '--timeout'):
            timeout = int(value)

        if option in ('-c', '--code'):
            statuses.append(int(value))

        if option in ('-b', '--body'):
            inbody = value

        if option in ('-g', '--gcore'):
            gcore = value

        if option in ('-d', '--coredir'):
            coredir = value

        if option in ('-e', '--eager'):
            eager = True

        if option in ('-E', '--not-eager'):
            eager = False

        if option in ('-n', '--name'):
            name = value

    if not statuses:
        statuses = [200]

    url = arguments[-1]

    try:
        rpc = childutils.getRPCInterface(os.environ)
    except KeyError as e:
        if e.args[0] != 'SUPERVISOR_SERVER_URL':
            raise
        sys.stderr.write('httpok must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return

    prog = HTTPOk(rpc, programs, any, url, timeout, statuses, inbody, email,
                  sendmail, coredir, gcore, eager, retry_time, name)
    prog.runforever()

if __name__ == '__main__':
    main()
