import unittest
import mock
from StringIO import StringIO

class FatalMailBatchTests(unittest.TestCase):
    fromEmail = 'testFrom@blah.com'
    toEmail = 'testTo@blah.com'
    subject = 'Test Alert'
    unexpectedErrorMsg = 'Process bar:foo failed to start too many times'
    
    def _getTargetClass(self):
        from superlance.fatalmailbatch import FatalMailBatch
        return FatalMailBatch
        
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

    def getProcessFatalEvent(self, pname, gname):
        headers = {
            'ver': '3.0', 'poolserial': '7', 'len': '71',
            'server': 'supervisor', 'eventname': 'PROCESS_STATE_FATAL',
            'serial': '7', 'pool': 'checkmailbatch',
        }
        payload = 'processname:%s groupname:%s from_state:BACKOFF' \
                % (pname, gname)
        return (headers, payload)
        
    def test_getProcessStateChangeMsg(self):
        crash = self._makeOneMocked()
        hdrs, payload = self.getProcessFatalEvent('foo', 'bar')
        msg = crash.getProcessStateChangeMsg(hdrs, payload)
        self.failUnless(self.unexpectedErrorMsg in msg)
        
if __name__ == '__main__':
    unittest.main()