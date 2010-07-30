import unittest
import mock
from StringIO import StringIO

class CrashMailBatchTests(unittest.TestCase):
    fromEmail = 'testFrom@blah.com'
    toEmail = 'testTo@blah.com'
    subject = 'Test Alert'
    unexpectedErrorMsg = 'Process bar:foo (pid 58597) died unexpectedly'

    def _getTargetClass(self):
        from superlance.crashmailbatch import CrashMailBatch
        return CrashMailBatch
        
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

    def getProcessExitedEvent(self, pname, gname, expected):
        headers = {
            'ver': '3.0', 'poolserial': '7', 'len': '71',
            'server': 'supervisor', 'eventname': 'PROCESS_STATE_EXITED',
            'serial': '7', 'pool': 'checkmailbatch',
        }
        payload = 'processname:%s groupname:%s from_state:RUNNING expected:%d \
pid:58597' % (pname, gname, expected)
        return (headers, payload)
        
    def test_getProcessStateChangeMsg_expected(self):
        crash = self._makeOneMocked()
        hdrs, payload = self.getProcessExitedEvent('foo', 'bar', 1)
        self.assertEquals(None, crash.getProcessStateChangeMsg(hdrs, payload))

    def test_getProcessStateChangeMsg_unexpected(self):
        crash = self._makeOneMocked()
        hdrs, payload = self.getProcessExitedEvent('foo', 'bar', 0)
        msg = crash.getProcessStateChangeMsg(hdrs, payload)
        self.failUnless(self.unexpectedErrorMsg in msg)
        
    def test_handleEvent_exit_expected(self):
        crash = self._makeOneMocked()
        hdrs, payload = self.getProcessExitedEvent('foo', 'bar', 1)
        crash.handleEvent(hdrs, payload)
        self.assertEquals([], crash.getBatchMsgs())
        self.assertEquals('', crash.stderr.getvalue())

    def test_handleEvent_exit_unexpected(self):
        crash = self._makeOneMocked()
        hdrs, payload = self.getProcessExitedEvent('foo', 'bar', 0)
        crash.handleEvent(hdrs, payload)
        msgs = crash.getBatchMsgs()
        self.assertEquals(1, len(msgs))
        self.failUnless(self.unexpectedErrorMsg in msgs[0])
        self.failUnless(self.unexpectedErrorMsg in crash.stderr.getvalue())

if __name__ == '__main__':
    unittest.main()         