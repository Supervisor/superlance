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
import time
from mmap import mmap
# Using old reference for Python 2.4
from email.MIMEText import MIMEText
from email.Utils import formatdate, make_msgid
# from email.mime.text import MIMEText
from superlance.process_state_monitor import ProcessStateMonitor
#from supervisor.rpcinterface import SupervisorNamespaceRPCInterface

doc = """\
Base class for common functionality when monitoring process state changes
and sending email notification
"""

class ProcessStateEmailMonitor(ProcessStateMonitor):
    COMMASPACE = ', '
    LOG_LEN_LIMIT = [0, 1024]

    @classmethod
    def _get_opt_parser(cls):
        from optparse import OptionParser

        parser = OptionParser()
        parser.add_option("-i", "--interval", dest="interval", type="float", default=1.0,
                        help="batch interval in minutes (defaults to 1 minute)")
        parser.add_option("-t", "--toEmail", dest="to_emails",
                        help="destination email address(es) - comma separated")
        parser.add_option("-f", "--fromEmail", dest="from_email",
                        help="source email address")
        parser.add_option("-s", "--subject", dest="subject",
                        help="email subject")
        parser.add_option("-T", "--addText", dest="text_in_body", default="",
                        help="add text in email body (defaults to empty)")
        parser.add_option("-S", "--addState", dest="state_in_body", default=False,
                        help="add state in email body (defaults to False)")
        parser.add_option("-l", "--addLog", dest="log_in_body", default="0",
                        help="add log in email body (defaults to 0")
        parser.add_option("-H", "--smtpHost", dest="smtp_host", default="localhost",
                        help="SMTP server hostname or address")
        parser.add_option("-e", "--tickEvent", dest="eventname", default="TICK_60",
                        help="TICK event name (defaults to TICK_60)")
        parser.add_option("-u", "--userName", dest="smtp_user", default="",
                        help="SMTP server user name (defaults to nothing)")
        parser.add_option("-p", "--password", dest="smtp_password", default="",
                        help="SMTP server password (defaults to nothing)")
        return parser
      
    @classmethod
    def parse_cmd_line_options(cls):
        parser = cls._get_opt_parser()
        (options, args) = parser.parse_args()
        return options

    @classmethod
    def validate_cmd_line_options(cls, options):
        parser = cls._get_opt_parser()
        if not options.to_emails:
            parser.print_help()
            sys.exit(1)
        if not options.from_email:
            parser.print_help()
            sys.exit(1)

        validated = copy.copy(options)
        validated.to_emails = [x.strip() for x in options.to_emails.split(",")]
        return validated

    @classmethod
    def get_cmd_line_options(cls):
        return cls.validate_cmd_line_options(cls.parse_cmd_line_options())

    @classmethod
    def create_from_cmd_line(cls):
        options = cls.get_cmd_line_options()

        if not 'SUPERVISOR_SERVER_URL' in os.environ:
            sys.stderr.write('Must run as a supervisor event listener\n')
            sys.exit(1)

        return cls(**options.__dict__)

    def __init__(self, **kwargs):
        ProcessStateMonitor.__init__(self, **kwargs)

        self.from_email = kwargs['from_email']
        self.to_emails = kwargs['to_emails']
        self.subject = kwargs.get('subject')
        self.text = kwargs.get('text_in_body', '')
        self.log_len = int(kwargs.get('log_in_body', '0'))
        self.add_state = kwargs.get('state_in_body', False)
        self.smtp_host = kwargs.get('smtp_host', 'localhost')
        self.smtp_user = kwargs.get('smtp_user')
        self.smtp_password = kwargs.get('smtp_password')
        self.digest_len = 76

        self._set_batch_text()
        self._set_batch_log_len()

    def _set_batch_msg(self):
        return '\n'.join(self.get_batch_msgs())

    def _set_batch_text(self):
        if self.text:
            self.text = "\n\n%s\n\n" % self.text

    def _set_batch_state(self):
        state = ''

        if not (self.text or self.log_len > self.LOG_LEN_LIMIT[0]):
            state = '\n\n'

        if self.add_state:
            proc_config = self.get_batch_proc()['config']

            if proc_config:
                state += 'Current state:\n'
                state += "    Status: %s\n" % proc_config['statename']
                state += "    PID: %s\n" % proc_config['pid']
                state += "    Start time: %s" % time.ctime(proc_config['start'])
            else:
                state += 'Current state can not be defined.'
            state += '\n\n'

        return state

    def _read_log_file(self, log_file_name, log_len):
        # open the file and mmap it
        log_file = open(log_file_name, 'r+')
        mm = mmap(log_file.fileno(), os.path.getsize(log_file.name))

        nl_count = 0
        i = mm.size() - 1

        if mm[i] == '\n':
            log_len += 1
        while nl_count < log_len and i > 0:
            if mm[i] == '\n':
                nl_count += 1
            i -= 1
        if i > 0:
            i += 2

        return mm[i:]

    def _set_batch_log_len(self):
        if self.log_len < self.LOG_LEN_LIMIT[0]:
            self.log_len = self.LOG_LEN_LIMIT[0]
        elif self.log_len > self.LOG_LEN_LIMIT[1]:
            self.log_len = self.LOG_LEN_LIMIT[1]
        else:
            pass

    def _set_batch_log(self):
        log_text = ''

        if not self.text:
            log_text = '\n\n'

        if not self.log_len == self.LOG_LEN_LIMIT[0]:
            proc_config = self.get_batch_proc()['config']

            if proc_config:
                log_file_name = proc_config['stdout_logfile']

                if log_file_name:
                    log_text += "Log (file %s):\n" % log_file_name
                    log_text += self._read_log_file(log_file_name, self.log_len)
                else:
                    log_text += 'Log file name can not be defined.'
            else:
                log_text += 'Log can not be defined.'
            log_text += '\n\n'

        return log_text

    def send_batch_notification(self):
        email = self.get_batch_email()
        if email:
            self.send_email(email)
            self.log_email(email)

    def log_email(self, email):
        email_for_log = copy.copy(email)
        email_for_log['to'] = self.COMMASPACE.join(email['to'])
        if len(email_for_log['body']) > self.digest_len:
            email_for_log['body'] = '%s...' % email_for_log['body'][:self.digest_len]
        self.write_stderr("Sending notification email:\nTo: %(to)s\n\
From: %(from)s\nSubject: %(subject)s\nBody:\n%(body)s\n" % email_for_log)

    def get_batch_email(self):
        if len(self.batchmsgs):
            return {
                'to': self.to_emails,
                'from': self.from_email,
                'subject': self.subject,
                'body': "%s%s%s%s" % (self._set_batch_msg(),
                                      self.text,
                                      self._set_batch_log(),
                                      self._set_batch_state()),
            }
        return None

    def send_email(self, email):
        msg = MIMEText(email['body'])
        if self.subject:
            msg['Subject'] = email['subject']
        msg['From'] = email['from']
        msg['To'] = self.COMMASPACE.join(email['to'])
        msg['Date'] = formatdate()
        msg['Message-ID'] = make_msgid()

        try:
            self.send_smtp(msg, email['to'])
        except Exception, e:
            self.write_stderr("Error sending email: %s\n" % e)

    def send_smtp(self, mime_msg, to_emails):
        s = smtplib.SMTP(self.smtp_host)
        try:
            if self.smtp_user and self.smtp_password:
                s.login(self.smtp_user,self.smtp_password)
            s.sendmail(mime_msg['From'], to_emails, mime_msg.as_string())
        except:
            s.quit()
            raise
        s.quit()

