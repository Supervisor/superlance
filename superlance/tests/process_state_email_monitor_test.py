import unittest
import mock
import time
from StringIO import StringIO

class ProcessStateEmailMonitorTests(unittest.TestCase):
    fromEmail = 'testFrom@blah.com'
    toEmail = 'testTo@blah.com'
    subject = 'Test Alert'
    
    def _getTargetClass(self):
        from superlance.process_state_email_monitor \
        import ProcessStateEmailMonitor
        return ProcessStateEmailMonitor
        
    def _makeOneMocked(self, **kwargs):
        kwargs['stdin'] = StringIO()
        kwargs['stdout'] = StringIO()
        kwargs['stderr'] = StringIO()
        kwargs['fromEmail'] = kwargs.get('fromEmail', self.fromEmail)
        kwargs['toEmail'] = kwargs.get('toEmail', self.toEmail)
        kwargs['subject'] = kwargs.get('subject', self.subject)
        
        obj = self._getTargetClass()(**kwargs)
        obj.sendEmail = mock.Mock()
        return obj
    
    def test_sendBatchNotification(self):
        testMsgs = ['msg1', 'msg2']
        monitor = self._makeOneMocked()
        monitor.batchMsgs = testMsgs
        monitor.sendBatchNotification()
        
        #Test that email was sent
        self.assertEquals(1, monitor.sendEmail.call_count)
        emailCallArgs = monitor.sendEmail.call_args[0]
        self.assertEquals(1, len(emailCallArgs))
        expected = {
            'body': 'msg1\nmsg2',
            'to': 'testTo@blah.com',
            'from': 'testFrom@blah.com',
            'subject': 'Test Alert',
        }
        self.assertEquals(expected, emailCallArgs[0])
        
        #Test that email was logged
        self.assertEquals("""Sending notification email:
To: testTo@blah.com
From: testFrom@blah.com
Subject: Test Alert
Body:
msg1
msg2
""", monitor.stderr.getvalue())
        
    def test_logEmail_with_body_digest(self):
        monitor = self._makeOneMocked()
        email = {
            'to': 'you@fubar.com',
            'from': 'me@fubar.com',
            'subject': 'yo yo',
            'body': 'a' * 30,
        }
        monitor.logEmail(email)
        self.assertEquals("""Sending notification email:
To: you@fubar.com
From: me@fubar.com
Subject: yo yo
Body:
aaaaaaaaaaaaaaaaaaaa...
""", monitor.stderr.getvalue())
        self.assertEquals('a' * 30, email['body'])

    def test_logEmail_without_body_digest(self):
        monitor = self._makeOneMocked()
        email = {
            'to': 'you@fubar.com',
            'from': 'me@fubar.com',
            'subject': 'yo yo',
            'body': 'a' * 20,
        }
        monitor.logEmail(email)
        self.assertEquals("""Sending notification email:
To: you@fubar.com
From: me@fubar.com
Subject: yo yo
Body:
aaaaaaaaaaaaaaaaaaaa
""", monitor.stderr.getvalue())

if __name__ == '__main__':
    unittest.main()