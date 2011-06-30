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
import os
import sys
import smtplib
import copy
# Using old reference for Python 2.4
from email.MIMEText import MIMEText
# from email.mime.text import MIMEText
from superlance.process_state_monitor import ProcessStateMonitor

doc = """\
Base class for common functionality when monitoring process state changes
and sending email notification
"""

class ProcessStateEmailMonitor(ProcessStateMonitor):

    @classmethod
    def create_from_cmd_line(cls):
        from optparse import OptionParser

        parser = OptionParser()
        parser.add_option("-i", "--interval", dest="interval", type="float", default=1.0,
                          help="batch interval in minutes (defaults to 1 minute)")
        parser.add_option("-t", "--toEmail", dest="to_email",
                          help="destination email address")
        parser.add_option("-f", "--fromEmail", dest="from_email",
                          help="source email address")
        parser.add_option("-s", "--subject", dest="subject",
                          help="email subject")
        parser.add_option("-H", "--smtpHost", dest="smtp_host", default="localhost",
                          help="SMTP server hostname or address")
        parser.add_option("-e", "--tickEvent", dest="eventname", default="TICK_60",
                          help="TICK event name (defaults to TICK_60)")
        
        (options, args) = parser.parse_args()

        if not options.to_email:
            parser.print_help()
            sys.exit(1)
        if not options.from_email:
            parser.print_help()
            sys.exit(1)

        if not 'SUPERVISOR_SERVER_URL' in os.environ:
            sys.stderr.write('Must run as a supervisor event listener\n')
            sys.exit(1)

        return cls(**options.__dict__)

    def __init__(self, **kwargs):
        ProcessStateMonitor.__init__(self, **kwargs)

        self.from_email = kwargs['from_email']
        self.to_email = kwargs['to_email']
        self.subject = kwargs.get('subject')
        self.smtp_host = kwargs.get('smtp_host', 'localhost')
        self.digest_len = 76

    def send_batch_notification(self):
        email = self.get_batch_email()
        if email:
            self.send_email(email)
            self.log_email(email)

    def log_email(self, email):
        email_for_log = copy.copy(email)
        if len(email_for_log['body']) > self.digest_len:
            email_for_log['body'] = '%s...' % email_for_log['body'][:self.digest_len]
        self.write_stderr("Sending notification email:\nTo: %(to)s\n\
From: %(from)s\nSubject: %(subject)s\nBody:\n%(body)s\n" % email_for_log)

    def get_batch_email(self):
        if len(self.batchmsgs):
            return {
                'to': self.to_email,
                'from': self.from_email,
                'subject': self.subject,
                'body': '\n'.join(self.get_batch_msgs()),
            }
        return None

    def send_email(self, email):
        msg = MIMEText(email['body'])
        if self.subject:
          msg['Subject'] = email['subject']
        msg['From'] = email['from']
        msg['To'] = email['to']

        try:
            self.send_smtp(msg)
        except Exception, e:
            self.write_stderr("Error sending email: %s\n" % e)

    def send_smtp(self, mimeMsg):
        s = smtplib.SMTP(self.smtp_host)
        try:
            s.sendmail(mimeMsg['From'], [mimeMsg['To']], mimeMsg.as_string())
        except:
            s.quit()
            raise
        s.quit()

