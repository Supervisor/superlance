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
# events, which restarts any processes that are children of
# supervisord that consume "too much" memory.  Performs horrendous
# screenscrapes of ps output.  Works on Linux and OS X (Tiger/Leopard)
# as far as I know.

# A supervisor config snippet that tells supervisor to use this script
# as a listener is below.
#
# [eventlistener:memmon]
# command=python memmon.py [options]
# events=TICK_60

doc = """\
memmon.py [-c] [-p processname=byte_size] [-g groupname=byte_size]
          [-a byte_size] [-s sendmail] [-m email_address]
          [-u uptime] [-n memmon_name]

Options:

-c -- Check against cumulative RSS. When calculating a process' RSS, also
      consider its child processes. With this option `memmon` will sum up
      the RSS of the process to be monitored and all its children.

-p -- specify a process_name=byte_size pair.  Restart the supervisor
      process named 'process_name' when it uses more than byte_size
      RSS.  If this process is in a group, it can be specified using
      the 'process_name:group_name' syntax.

-g -- specify a group_name=byte_size pair.  Restart any process in this group
      when it uses more than byte_size RSS.

-a -- specify a global byte_size.  Restart any child of the supervisord
      under which this runs if it uses more than byte_size RSS.

-s -- the sendmail command to use to send email
      (e.g. "/usr/sbin/sendmail -t -i").  Must be a command which accepts
      header and message data on stdin and sends mail.
      Default is "/usr/sbin/sendmail -t -i".

-m -- specify an email address.  The script will send mail to this
      address when any process is restarted.  If no email address is
      specified, email will not be sent.

-u -- optionally specify the minimum uptime in seconds for the process.
      if the process uptime is longer than this value, no email is sent
      (useful to only be notified if processes are restarted too often/early)

      seconds can be specified as plain integer values or a suffix-multiplied integer
      (e.g. 1m). Valid suffixes are m (minute), h (hour) and d (day).

-n -- optionally specify the name of the memmon process. This name will
      be used in the email subject to identify which memmon process
      restarted the process.

The -p and -g options may be specified more than once, allowing for
specification of multiple groups and processes.

Any byte_size can be specified as a plain integer (10000) or a
suffix-multiplied integer (e.g. 1GB).  Valid suffixes are 'KB', 'MB'
and 'GB'.

A sample invocation:

memmon.py -p program1=200MB -p theprog:thegroup=100MB -g thegroup=100MB -a 1GB -s "/usr/sbin/sendmail -t -i" -m chrism@plope.com -n "Project 1"
"""

import os
import sys
import time
import xmlrpclib
from collections import namedtuple

from supervisor import childutils
from supervisor.datatypes import byte_size, SuffixMultiplier

def usage():
    print doc
    sys.exit(255)

def shell(cmd):
    return os.popen(cmd).read()

class Memmon:
    def __init__(self, cumulative, programs, groups, any, sendmail, email, email_uptime_limit, name, rpc=None):
        self.cumulative = cumulative
        self.programs = programs
        self.groups = groups
        self.any = any
        self.sendmail = sendmail
        self.email = email
        self.email_uptime_limit = email_uptime_limit
        self.memmonName = name
        self.rpc = rpc
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.pscommand = 'ps -orss= -p %s'
        self.pstreecommand = 'ps ax -o "pid= ppid= rss="'
        self.mailed = False # for unit tests

    def runforever(self, test=False):
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

            status = []
            if self.programs:
                status.append(
                    'Checking programs %s' % ', '.join(
                    [ '%s=%s' % x for x in self.programs.items() ] )
                    )

            if self.groups:
                status.append(
                    'Checking groups %s' % ', '.join(
                    [ '%s=%s' % x for x in self.groups.items() ] )
                    )
            if self.any is not None:
                status.append('Checking any=%s' % self.any)

            self.stderr.write('\n'.join(status) + '\n')

            infos = self.rpc.supervisor.getAllProcessInfo()

            for info in infos:
                pid = info['pid']
                name = info['name']
                group = info['group']
                pname = '%s:%s' % (group, name)

                if not pid:
                    # ps throws an error in this case (for processes
                    # in standby mode, non-auto-started).
                    continue

                rss = self.calc_rss(pid)
                if rss is None:
                    # no such pid (deal with race conditions) or
                    # rss couldn't be calculated for other reasons
                    continue

                for n in name, pname:
                    if n in self.programs:
                        self.stderr.write('RSS of %s is %s\n' % (pname, rss))
                        if  rss > self.programs[name]:
                            self.restart(pname, rss)
                            continue

                if group in self.groups:
                    self.stderr.write('RSS of %s is %s\n' % (pname, rss))
                    if rss > self.groups[group]:
                        self.restart(pname, rss)
                        continue

                if self.any is not None:
                    self.stderr.write('RSS of %s is %s\n' % (pname, rss))
                    if rss > self.any:
                        self.restart(pname, rss)
                        continue

            self.stderr.flush()
            childutils.listener.ok(self.stdout)
            if test:
                break

    def restart(self, name, rss):
        info = self.rpc.supervisor.getProcessInfo(name)
        uptime = info['now'] - info['start'] #uptime in seconds
        self.stderr.write('Restarting %s\n' % name)
        memmonId = self.memmonName and " [%s]" % self.memmonName or ""
        try:
            self.rpc.supervisor.stopProcess(name)
        except xmlrpclib.Fault, what:
            msg = ('Failed to stop process %s (RSS %s), exiting: %s' %
                   (name, rss, what))
            self.stderr.write(str(msg))
            if self.email:
                subject = 'memmon%s: failed to stop process %s, exiting' % (memmonId, name)
                self.mail(self.email, subject, msg)
            raise

        try:
            self.rpc.supervisor.startProcess(name)
        except xmlrpclib.Fault, what:
            msg = ('Failed to start process %s after stopping it, '
                   'exiting: %s' % (name, what))
            self.stderr.write(str(msg))
            if self.email:
                subject = 'memmon%s: failed to start process %s, exiting' % (memmonId, name)
                self.mail(self.email, subject, msg)
            raise

        if self.email and uptime <= self.email_uptime_limit:
            now = time.asctime()
            msg = (
                'memmon.py restarted the process named %s at %s because '
                'it was consuming too much memory (%s bytes RSS)' % (
                name, now, rss)
                )
            subject = 'memmon%s: process %s restarted' % (memmonId, name)
            self.mail(self.email, subject, msg)

    def calc_rss(self, pid):

        ProcInfo = namedtuple('ProcInfo', ['pid', 'ppid', 'rss'])

        def find_children(parent_pid, procs):
            children = []
            for proc in procs:
                pid, ppid, rss = proc
                if ppid == parent_pid:
                    children.append(proc)
                    children.extend(find_children(pid, procs))
            return children

        def cum_rss(pid, procs):
            parent_proc = [p for p in procs if p.pid == pid][0]
            children = find_children(pid, procs)
            tree = [parent_proc] + children
            total_rss = sum(map(int, [p.rss for p in tree]))
            return total_rss

        def get_all_process_infos(data):
            data = data.strip()
            procs = []
            for line in data.splitlines():
                pid, ppid, rss = map(int, line.split())
                procs.append(ProcInfo(pid=pid, ppid=ppid, rss=rss))
            return procs

        if self.cumulative:
            data = shell(self.pstreecommand)
            procs = get_all_process_infos(data)

            try:
                rss = cum_rss(pid, procs)
            except (ValueError, IndexError):
                # Could not determine cumulative RSS
                return None

        else:
            data = shell(self.pscommand % pid)
            if not data:
                # no such pid (deal with race conditions)
                return None

            try:
                rss = data.lstrip().rstrip()
                rss = int(rss)
            except ValueError:
                # line doesn't contain any data, or rss cant be intified
                return None

        rss = rss * 1024  # rss is in KB
        return rss

    def mail(self, email, subject, msg):
        body = 'To: %s\n' % self.email
        body += 'Subject: %s\n' % subject
        body += '\n'
        body += msg
        m = os.popen(self.sendmail, 'w')
        m.write(body)
        m.close()
        self.mailed = body

def parse_namesize(option, value):
    try:
        name, size = value.split('=')
    except ValueError:
        print 'Unparseable value %r for %r' % (value, option)
        usage()
    size = parse_size(option, size)
    return name, size

def parse_size(option, value):
    try:
        size = byte_size(value)
    except:
        print 'Unparseable byte_size in %r for %r' % (value, option)
        usage()

    return size

seconds_size = SuffixMultiplier({'s': 1,
                                 'm': 60,
                                 'h': 60 * 60,
                                 'd': 60 * 60 * 24
                                 })

def parse_seconds(option, value):
    try:
        seconds = seconds_size(value)
    except:
        print 'Unparseable value for time in %r for %s' % (value, option)
        usage()
    return seconds

def memmon_from_args(arguments):
    import getopt
    short_args = "hcp:g:a:s:m:n:u:"
    long_args = [
        "help",
        "cumulative",
        "program=",
        "group=",
        "any=",
        "sendmail_program=",
        "email=",
        "uptime=",
        "name=",
        ]

    if not arguments:
        return None
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        return None

    cumulative = False
    programs = {}
    groups = {}
    any = None
    sendmail = '/usr/sbin/sendmail -t -i'
    email = None
    uptime_limit = sys.maxint
    name = None

    for option, value in opts:

        if option in ('-h', '--help'):
            return None

        if option in ('-c', '--cumulative'):
            cumulative = True

        if option in ('-p', '--program'):
            name, size = parse_namesize(option, value)
            programs[name] = size

        if option in ('-g', '--group'):
            name, size = parse_namesize(option, value)
            groups[name] = size

        if option in ('-a', '--any'):
            size = parse_size(option, value)
            any = size

        if option in ('-s', '--sendmail_program'):
            sendmail = value

        if option in ('-m', '--email'):
            email = value

        if option in ('-u', '--uptime'):
            uptime_limit = parse_seconds(option, value)

        if option in ('-n', '--name'):
            name = value

    memmon = Memmon(cumulative=cumulative,
                    programs=programs,
                    groups=groups,
                    any=any,
                    sendmail=sendmail,
                    email=email,
                    email_uptime_limit=uptime_limit,
                    name=name)
    return memmon

def main():
    memmon = memmon_from_args(sys.argv[1:])
    if memmon is None:
        # something went wrong or -h has been given
        usage()
    memmon.rpc = childutils.getRPCInterface(os.environ)
    memmon.runforever()

if __name__ == '__main__':
    main()



