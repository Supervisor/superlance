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

##############################################################################
# httpctrl
# author: Jaka Hudoklin (http://github.com/offlinehacker)
##############################################################################

# A event listener meant to be subscribed to TICK_60 (or TICK_5)
# events, which restarts processes that are children of
# supervisord based on the response from an HTTP port.

# A supervisor config snippet that tells supervisor to use this script
# as a listener is below.
#
# [eventlistener:httpctrl]
# command=python -u /bin/httpctrl http://localhost:8080/control
# events=TICK_5

doc = """\
httpctrl.py [-p processname] [-a] [-b inbody] URL

Options:

-p -- specify a supervisor 'process_name' or 'group_name'. Starts
      the supervisor process if it's in STOPPED state and specified
      string is present in body of URL.
      Stops the supervisor process if it's in the RUNNING state when
      specified string is not present in the body of URL.
      If this process is part of a group, it can be specified using
      the 'group_name:process_name' syntax.

-b -- specify a string which should be present in the body resulting
      from the GET request. If this string is not present in the
      response, the processes in the RUNNING state specified by -p
      will be stopped in another case it will be started.

URL -- The URL to which to issue a GET request.

The -p option may be specified more than once, allowing for
specification of multiple processes.

A sample invocation:

httpctrl.py -p program1 -p group1 -p group1:program2 http://localhost:8080/control

"""

import os
import sys
import urlparse
import xmlrpclib

from supervisor import childutils
from supervisor.states import ProcessStates
from supervisor.options import make_namespec

import timeoutconn

def usage():
    print doc
    sys.exit(255)

class HTTPCtrl:
    def __init__(self, rpc, programs, url, inbody):
        self.rpc = rpc
        self.programs = programs
        self.url = url
        self.inbody = inbody

        self.timeout = 10

    def listProcesses(self, state=None):
        return [x for x in self.rpc.supervisor.getAllProcessInfo()
                   if (x['name'] in self.programs or x['group'] in self.programs) and
                      (state is None or x['state'] == state)]

    def write_stderr(self, msg):
        sys.stderr.write('%s\n' % msg)
        sys.stderr.flush()

    def parse_url(self):
        parsed = urlparse.urlsplit(self.url)
        scheme = parsed[0].lower()
        hostport = parsed[1]
        path = parsed[2]
        query = parsed[3]

        if query: path += '?' + query

        if scheme == 'http':
            ConnClass = timeoutconn.TimeoutHTTPConnection
        elif scheme == 'https':
            ConnClass = timeoutconn.TimeoutHTTPSConnection
        else:
            raise ValueError('Bad scheme %s' % scheme)

        return (ConnClass, hostport, path)

    def runforever(self):
        ConnClass, hostport, path = self.parse_url()
        while True:
            headers, payload = childutils.listener.wait()

            if not headers['eventname'].startswith('TICK'):
                # do nothing with non-TICK events
                continue

            conn = ConnClass(hostport)
            conn.timeout = self.timeout

            body = ''
            try:
                conn.request('GET', path)
                res = conn.getresponse()
                body = res.read()
            except Exception, why:
                self.write_stderr('error contacting %s:\n %s' % (self.url, why))
                continue

            if self.inbody not in body:
                if len(self.listProcesses(ProcessStates.RUNNING)) > 0:
                    self.act(start = False)
            else:
                if len(self.listProcesses(ProcessStates.STOPPED)) > 0:
                    self.act(start = True)

            childutils.listener.ok()

    def act(self, start = True):
        try:
            specs = self.rpc.supervisor.getAllProcessInfo()
        except Exception, why:
            self.write_stderr('Exception retrieving process info %s, not acting' % why)
            return

        waiting = list(self.programs)

        self.write_stderr('%s selected processes %s' %
                          ("Starting" if start else "Stopping", self.programs))
        for spec in specs:
            name = spec['name']
            group = spec['group']
            namespec = make_namespec(group, name)

            if (name in self.programs or
                group in self.programs or
                namespec in self.programs):

                self.start_stop(spec, start)
                if name in waiting:
                    waiting.remove(name)
                if group in waiting:
                    waiting.remove(group)
                if namespec in waiting:
                    waiting.remove(namespec)

        if waiting:
            self.write_stderr(
                'Programs states not changed because they did not exist: %s' %
                waiting)

    def start_stop(self, spec, start=True):
        namespec = make_namespec(spec['group'], spec['name'])
        if spec['state'] is ProcessStates.RUNNING and not start:
            self.write_stderr('%s is in RUNNING state, stopping' % namespec)
            try:
                self.rpc.supervisor.stopProcess(namespec)
            except xmlrpclib.Fault, what:
                self.write_stderr('Failed to stop process %s: %s' %
                                   (namespec, what))
            else:
                self.write_stderr('%s stopped' % namespec)

        elif spec['state'] is ProcessStates.STOPPED and start:
            self.write_stderr('%s is in STOPPED state, starting' % namespec)
            try:
                self.rpc.supervisor.startProcess(namespec)
            except xmlrpclib.Fault, what:
                self.write_stderr('Failed to start process %s: %s' %
                                  (namespec, what))
            else:
                self.write_stderr('%s started' % namespec)

def main(argv=sys.argv):
    import getopt
    short_args="hp:b:"
    long_args=[
        "help",
        "program=",
        "body=",
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
    inbody = None

    for option, value in opts:

        if option in ('-h', '--help'):
            usage()

        if option in ('-p', '--program'):
            programs.append(value)

        if option in ('-b', '--body'):
            inbody = value

    url = arguments[-1]

    try:
        rpc = childutils.getRPCInterface(os.environ)
    except KeyError, why:
        if why[0] != 'SUPERVISOR_SERVER_URL':
            raise
        sys.stderr.write('httpctrl must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return

    prog = HTTPCtrl(rpc, programs, url, inbody)
    prog.runforever()

if __name__ == '__main__':
    main()
