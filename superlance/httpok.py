#!/usr/bin/env python
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
    [-B restart_string] [-m mail_address] [-s sendmail] [-r restart_threshold]
    [-n restart_timespan] [-x external_script] URL

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
      RUNNING state specified by -p or -a.  This defaults to the
      string, "200".

-b -- specify a string which should be present in the body resulting
      from the GET request.  If this string is not present in the
      response, the processes in the RUNNING state specified by -p
      or -a will be restarted.  The default is to ignore the
      body.

-B -- specify a string which should NOT be present in the body resulting
      from the GET request. If this string is present in the
      response, the processes in the RUNNING state specified by -p
      or -a will be restarted.  This option is the opposite of the -b option
      and can be specified multiple times and it may be specified along with
      the -b option. The default is to ignore the restart string.

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

-r -- specify the maximum number of times program should be restarted if it 
      does not return successful result while issuing a GET. 0 - for unlimited
      number of restarts. Default is 3.

-n -- specify the time span in minutes during which the maximum number of
      restarts could happen. This prevents loop restarts when the application
      is running fine for configured TICK seconds then starts to fail again.
      Default is 60.

-x -- optionally specify an external script to restart the program, e.g.
      /etc/init.d/myprogramservicescript.

URL -- The URL to which to issue a GET request.

The -p option may be specified more than once, allowing for
specification of multiple processes.  Specifying -a overrides any
selection of -p.

A sample invocation:

httpok.py -p program1 -p group1:program2 http://localhost:8080/tasty

"""

import os
import socket
import sys
import time
from superlance.compat import urlparse
from superlance.compat import xmlrpclib
from superlance.utils import ExternalService

from supervisor import childutils
from supervisor.states import ProcessStates
from supervisor.options import make_namespec

from superlance import timeoutconn

def usage():
    print(doc)
    sys.exit(255)

class HTTPOk:
    connclass = None
    # For backward compatibility setting restart argument defaults to 0 and
    # ext_service to None
    def __init__(self, rpc, programs, any, url, timeout, status, inbody,
                 email, sendmail, coredir, gcore, eager, retry_time,
                 restart_threshold=0, restart_timespan=0, ext_service=None,
                 restart_string=None):
        self.rpc = rpc
        self.programs = programs
        self.any = any
        self.url = url
        self.timeout = timeout
        self.retry_time = retry_time
        self.status = status
        self.inbody = inbody
        self.restart_string = restart_string
        self.email = email
        self.sendmail = sendmail
        self.coredir = coredir
        self.gcore = gcore
        self.eager = eager
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.counter = {}
        self.restart_threshold = restart_threshold
        self.restart_timespan = restart_timespan * 60
        self.ext_service = ext_service

    def listProcesses(self, state=None):
        return [x for x in self.rpc.supervisor.getAllProcessInfo()
                   if x['name'] in self.programs and
                      (state is None or x['state'] == state)]

    def runforever(self, test=False):
        parsed = urlparse.urlsplit(self.url)
        scheme = parsed[0].lower()
        hostport = parsed[1]
        path = parsed[2]
        query = parsed[3]

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

                if str(status) != str(self.status):
                    subject = 'httpok for %s: bad status returned' % self.url
                    self.act(subject, msg)
                elif self.inbody and self.inbody not in body:
                    subject = 'httpok for %s: bad body returned' % self.url
                    self.act(subject, msg)
                elif self.restart_string and isinstance(self.restart_string,
                                                        list):
                    if any(restart_string in body for restart_string in
                           self.restart_string):
                        subject = 'httpok for %s: restart string in body' % \
                                  self.url
                        self.act(subject, msg)
                if [ spec for spec, value in self.counter.items()
                      if value['counter'] > 0]:
                    # Null the counters if timespan is over
                    self.cleanCounters()

            childutils.listener.ok(self.stdout)
            if test:
                break

    def act(self, subject, msg):
        messages = [msg]
        email = True

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
                if self.restartCounter(spec, write):
                    self.restart(spec, write)
                else:
                    email = False
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
                    if self.restartCounter(spec, write):
                        self.restart(spec, write)
                    else:
                        email = False
                    if name in waiting:
                        waiting.remove(name)
                    if namespec in waiting:
                        waiting.remove(namespec)

        if waiting:
            write(
                'Programs not restarted because they did not exist: %s' %
                waiting)

        if self.email and email:
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
            if self.ext_service:
                try:
                    self.ext_service.stopProcess(namespec)
                except Exception as e:
                    write('Failed to stop process %s: %s' % (
                        namespec, e))
                try:
                    self.ext_service.startProcess(namespec)
                except Exception as e:
                    write('Failed to start process %s: %s' % (
                        namespec, e))
                else:
                    write('%s restarted' % namespec)
            else:
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
            if spec['name'] in self.counter:
                new_spec = self.rpc.supervisor.getProcessInfo(spec['name'])
                self.counter[spec['name']]['last_pid'] = new_spec['pid']
        else:
            write('%s not in RUNNING state, NOT restarting' % namespec)
            
    def restartCounter(self, spec, write):
        """
        Function to check if number of restarts exceeds the configured
        restart_threshold and last restart time does not exceed
        restart_timespan. It will stop letting self.act() from restarting
        the program unless it is restarted externally, e.g. manually by a human
        
        :param spec: Spec as returned by RPC
        :type spec: dict struct
        :param write: Stderr write handler and a message container
        :type write: function
        :returns: Boolean result whether to continue or not
        """
        if spec['name'] not in self.counter:
            # Create a new counter and return True
            self.counter[spec['name']] = {}
            self.counter[spec['name']]['counter'] = 1
            self.counter[spec['name']]['last_pid'] = spec['pid']
            self.counter[spec['name']]['restart_time'] = time.time()
            write('%s restart is approved' % spec['name'])
            return True
        elif self.restart_threshold == 0:
            # Continue if we don't limit the number of restarts
            self.counter[spec['name']]['counter'] += 1
            self.counter[spec['name']]['restart_time'] = time.time()
            write('%s in restart loop, attempt: %s' % (spec['name'],
                self.counter[spec['name']]['counter']))
            return True
        else:
            if self.counter[spec['name']]['counter'] < self.restart_threshold:
                self.counter[spec['name']]['counter'] += 1
                write('%s restart attempt: %s' % (spec['name'],
                    self.counter[spec['name']]['counter']))
                return True
            # Do not let httpok restart the program
            else:
                write('Not restarting %s anymore. Restarted %s times' % (
                    spec['name'], self.counter[spec['name']]['counter']))
                return False
    
    def cleanCounters(self):
        """
        Function to clean the counter once all monitored programs are
        running properly and successfully respond to GET requests. It won't
        clean the counter if self.restart_timespan hasn't been passed
        """
        for spec in self.counter.keys():
            if ((time.time() - self.counter[spec]['restart_time']) >
                    self.restart_timespan):
                self.counter[spec]['restart_time'] = time.time()
                self.counter[spec]['counter'] = 0


def main(argv=sys.argv):
    import getopt
    short_args="hp:at:c:b:B:s:m:g:d:eEr:n:x:"
    long_args=[
        "help",
        "program=",
        "any",
        "timeout=",
        "code=",
        "body=",
        "restart-string=",
        "sendmail_program=",
        "email=",
        "gcore=",
        "coredir=",
        "eager",
        "not-eager",
        "restart-threshold=",
        "restart-timespan=",
        "external-service-script=",
        ]
    arguments = argv[1:]
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        usage()

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
    status = '200'
    inbody = None
    restart_string = []
    restart_threshold = 3
    restart_timespan = 60
    external_service_script = None

    for option, value in opts:

        if option in ('-h', '--help'):
            usage()

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
            status = value

        if option in ('-b', '--body'):
            inbody = value

        if option in ('-B', '--restart-string'):
            restart_string.append(value)

        if option in ('-g', '--gcore'):
            gcore = value

        if option in ('-d', '--coredir'):
            coredir = value

        if option in ('-e', '--eager'):
            eager = True

        if option in ('-E', '--not-eager'):
            eager = False
        
        if option in ('-r', '--restart-threshold'):
            try:
                restart_threshold = int(value)
            except ValueError:
                sys.stderr.write('Restart threshold should be a number\n')
                sys.stderr.flush()
                return
        
        if option in ('-n', '--restart-timespan'):
            try:
                restart_timespan = int(value)
            except ValueError:
                sys.stderr.write('Restart timespan should be a number\n')
                sys.stderr.flush()
                return
        
        if option in ('-x', '--external-service-script'):
            external_service_script = value

    url = arguments[-1]

    try:
        rpc = childutils.getRPCInterface(os.environ)
        if external_service_script:
            # Instantiate an ExternalService class to call the given script
            ext_service = ExternalService(external_service_script)
        else:
            ext_service = None
    except KeyError as e:
        if e.args[0] != 'SUPERVISOR_SERVER_URL':
            raise
        sys.stderr.write('httpok must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return
    except OSError as e:
        sys.stderr.write('os error occurred: %s\n' % e)
        sys.stderr.flush()
        return

    prog = HTTPOk(rpc, programs, any, url, timeout, status, inbody, email,
                  sendmail, coredir, gcore, eager, retry_time,
                  restart_threshold, restart_timespan, ext_service,
                  restart_string)
    prog.runforever()

if __name__ == '__main__':
    main()
