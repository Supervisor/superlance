import unittest
import mock
import time
from StringIO import StringIO

class ProcessStateEmailMonitorTestException(Exception):
    pass

class ProcessStateEmailMonitorTests(unittest.TestCase):
    fromEmail = 'testFrom@blah.com'
    toEmail = 'testTo@blah.com'
    subject = 'Test Alert'
    
    def _getTargetClass(self):
        from superlance.process_state_email_monitor \
        import ProcessStateEmailMonitor
        return ProcessStateEmailMonitor
    
    def _makeOne(self, **kwargs):
        kwargs['stdin'] = StringIO()
        kwargs['stdout'] = StringIO()
        kwargs['stderr'] = StringIO()
        kwargs['fromEmail'] = kwargs.get('fromEmail', self.fromEmail)
        kwargs['toEmail'] = kwargs.get('toEmail', self.toEmail)
        kwargs['subject'] = kwargs.get('subject', self.subject)
        
        obj = self._getTargetClass()(**kwargs)
        return obj
            
    def _makeOneMock_sendEmail(self, **kwargs):
        obj = self._makeOne(**kwargs)
        obj.sendEmail = mock.Mock()
        return obj

    def _makeOneMock_sendSMTP(self, **kwargs):
        obj = self._makeOne(**kwargs)
        obj.sendSMTP = mock.Mock()
        return obj
    
    def test_sendEmail_ok(self):
        email = {
            'body': 'msg1\nmsg2',
            'to': 'testTo@blah.com',
            'from': 'testFrom@blah.com',
            'subject': 'Test Alert',
        }
        monitor = self._makeOneMock_sendSMTP()
        monitor.sendEmail(email)
        
        #Test that email was sent
        self.assertEquals(1, monitor.sendSMTP.call_count)
        smtpCallArgs = monitor.sendSMTP.call_args[0]
        mimeMsg = smtpCallArgs[0]
        self.assertEquals(email['to'], mimeMsg['To'])
        self.assertEquals(email['from'], mimeMsg['From'])
        self.assertEquals(email['subject'], mimeMsg['Subject'])
        self.assertEquals(email['body'], mimeMsg.get_payload())

    def _raiseSTMPException(self, mimeMsg):
        raise ProcessStateEmailMonitorTestException('test')
        
    def test_sendEmail_exception(self):
        email = {
            'body': 'msg1\nmsg2',
            'to': 'testTo@blah.com',
            'from': 'testFrom@blah.com',
            'subject': 'Test Alert',
        }
        monitor = self._makeOneMock_sendSMTP()
        monitor.sendSMTP.side_effect = self._raiseSTMPException
        monitor.sendEmail(email)

        #Test that error was logged to stderr
        self.assertEquals("Error sending email: test", monitor.stderr.getvalue())
    
    def test_sendBatchNotification(self):
        testMsgs = ['msg1', 'msg2']
        monitor = self._makeOneMock_sendEmail()
        monitor.batchMsgs = testMsgs
        monitor.sendBatchNotification()
        
        #Test that email was sent
        expected = {
            'body': 'msg1\nmsg2',
            'to': 'testTo@blah.com',
            'from': 'testFrom@blah.com',
            'subject': 'Test Alert',
        }
        self.assertEquals(1, monitor.sendEmail.call_count)
        monitor.sendEmail.assert_called_with(expected)
        
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
        bodyLen = 80
        monitor = self._makeOneMock_sendEmail()
        email = {
            'to': 'you@fubar.com',
            'from': 'me@fubar.com',
            'subject': 'yo yo',
            'body': 'a' * bodyLen,
        }
        monitor.logEmail(email)
        self.assertEquals("""Sending notification email:
To: you@fubar.com
From: me@fubar.com
Subject: yo yo
Body:
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa...
""", monitor.stderr.getvalue())
        self.assertEquals('a' * bodyLen, email['body'])

    def test_logEmail_without_body_digest(self):
        monitor = self._makeOneMock_sendEmail()
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