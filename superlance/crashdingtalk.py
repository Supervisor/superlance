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
# events.  It will send mail when processes that are children of
# supervisord transition unexpectedly to the EXITED state.

# A supervisor config snippet that tells supervisor to use this script
# as a listener is below.
#
# [eventlistener:crashmail]
# command =
#     /usr/bin/crashmail
#         -o hostname -a -m notify-on-crash@domain.com
#         -s '/usr/sbin/sendmail -t -i -f crash-notifier@domain.com'
# events=PROCESS_STATE
#
# Sendmail is used explicitly here so that we can specify the 'from' address.

doc = """\
crashwxwork.py [-p processname] [-a] [-o string] [-m mail_address]
             [-s sendmail] URL

Options:

-p -- specify a supervisor process_name.  Send mail when this process
      transitions to the EXITED state unexpectedly. If this process is
      part of a group, it can be specified using the
      'group_name:process_name' syntax.

-a -- Send mail when any child of the supervisord transitions
      unexpectedly to the EXITED state unexpectedly.  Overrides any -p
      parameters passed in the same crashmail process invocation.

-wxwork_key -- Wxwork robot hook url key

The -p option may be specified more than once, allowing for
specification of multiple processes.  Specifying -a overrides any
selection of -p.

A sample invocation:

crashwxwork.py -p program1 -p group1:program2 -wxwork_key "key"

"""

import argparse
import sys
import urllib2
import urllib
import json
import time, hmac, hashlib, base64
import socket

from supervisor import childutils


def usage(exitstatus=255):
    print(doc)
    sys.exit(exitstatus)


class Crashwxwork(object):
    wxwork_hook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send'

    def __init__(self, programs, any, wxwork_key):

        self.programs = programs
        self.any = any
        self.wxwork_key = wxwork_key
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def runforever(self, test=False):
        while True:
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
            self.stderr.write('unexpected exit, mailing\n')
            self.stderr.flush()

            self.notify(subject, msg)

            childutils.listener.ok(self.stdout)
            if test:
                break

    def get_hostname(self):
        return socket.gethostname()

    def gen_dingtalk_secret(self):
        timestamp = long(round(time.time() * 1000))
        secret = self.dingtalk_secret
        sign = "{}\n{}".format(timestamp, secret)
        hash_hac = hmac.new(secret, sign, digestmod=hashlib.sha256).digest()
        sign = urllib.quote_plus(base64.b64encode(hash_hac))

        return timestamp, sign

    def notify(self, subject, msg):
        timestamp, sign = self.gen_dingtalk_secret()
        j = {
            "msgtype": "markdown",
            "markdown": {
                "title": "@所有人 From supervisor warning: %s" % subject,
                "content": """
                    ### supervisor warning {subject} \n
                    > hostname: {hostname} \n
                    > ### {msg} \n
                """.format(hostname=self.get_hostname(), subject=subject, msg=msg)
            }
        }

        r = urllib2.Request(self.wxwork_hook_url + "&key={}".format(self.wxwork_key), headers={
            "Content-Type": "application/json"
        })

        fp = urllib2.urlopen(r, data=json.dumps(j))
        fp.read()
        fp.close()


def main(argv=sys.argv):
    command_parser = argparse.ArgumentParser()
    command_parser.add_argument("-p", dest="programs", required=True, type=str, help=doc, action="append")
    command_parser.add_argument("-wxwork_key", dest="wxwork_key", type=str, required=True, help=doc)
    command_parser.add_argument("-a", dest="any", type=bool, required=False, help=doc, default=False)
    args = command_parser.parse_args()

    programs = args.programs
    prog = CrashDingtalk(programs, args.any, args.dingtalk_hook_url, args.dingtalk_secret)
    prog.runforever()


if __name__ == '__main__':
    main()
