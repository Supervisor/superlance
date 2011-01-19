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
    def createFromCmdLine(cls):
        from optparse import OptionParser

        parser = OptionParser()
        parser.add_option("-i", "--interval", dest="interval", type="int",
                          help="batch interval in minutes (defaults to 1 minute)")
        parser.add_option("-t", "--toEmail", dest="toEmail",
                          help="destination email address")
        parser.add_option("-f", "--fromEmail", dest="fromEmail",
                          help="source email address")
        parser.add_option("-s", "--subject", dest="subject",
                          help="email subject")
        parser.add_option("-H", "--smtpHost", dest="smtpHost", default="localhost",
                          help="SMTP server hostname or address")
        (options, args) = parser.parse_args()

        if not options.toEmail:
            parser.print_help()
            sys.exit(1)
        if not options.fromEmail:
            parser.print_help()
            sys.exit(1)

        if not 'SUPERVISOR_SERVER_URL' in os.environ:
            sys.stderr.write('Must run as a supervisor event listener\n')
            sys.exit(1)

        return cls(**options.__dict__)

    def __init__(self, **kwargs):
        ProcessStateMonitor.__init__(self, **kwargs)

        self.fromEmail = kwargs['fromEmail']
        self.toEmail = kwargs['toEmail']
        self.subject = kwargs.get('subject', 'Alert from supervisord')
        self.smtpHost = kwargs['smtpHost']
        self.digestLen = 76

    def sendBatchNotification(self):
        email = self.getBatchEmail()
        if email:
            self.sendEmail(email)
            self.logEmail(email)

    def logEmail(self, email):
        email4Log = copy.copy(email)
        if len(email4Log['body']) > self.digestLen:
            email4Log['body'] = '%s...' % email4Log['body'][:self.digestLen]
        self.writeToStderr("Sending notification email:\nTo: %(to)s\n\
From: %(from)s\nSubject: %(subject)s\nBody:\n%(body)s\n" % email4Log)

    def getBatchEmail(self):
        if len(self.batchMsgs):
            return {
                'to': self.toEmail,
                'from': self.fromEmail,
                'subject': self.subject,
                'body': '\n'.join(self.getBatchMsgs()),
            }
        return None

    def sendEmail(self, email):
        msg = MIMEText(email['body'])
        msg['Subject'] = email['subject']
        msg['From'] = email['from']
        msg['To'] = email['to']

        try:
            self.sendSMTP(msg)
        except Exception, e:
            self.writeToStderr("Error sending email: %s\n" % e)

    def sendSMTP(self, mimeMsg):
        s = smtplib.SMTP(self.smtpHost)
        try:
            s.sendmail(mimeMsg['From'], [mimeMsg['To']], mimeMsg.as_string())
        except:
            s.quit()
            raise
        s.quit()

