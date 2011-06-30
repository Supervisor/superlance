import unittest
import mock
import time
from StringIO import StringIO
from superlance.process_state_monitor import ProcessStateMonitor

class TestProcessStateMonitor(ProcessStateMonitor):
    
    processStateEvents = ['PROCESS_STATE_EXITED']
            
    def getProcessStateChangeMsg(self, headers, payload):
        return repr(payload)

class ProcessStateMonitorTests(unittest.TestCase):
    
    def _getTargetClass(self):
        return TestProcessStateMonitor
        
    def _makeOneMocked(self, **kwargs):
        kwargs['stdin'] = StringIO()
        kwargs['stdout'] = StringIO()
        kwargs['stderr'] = StringIO()
        
        obj = self._getTargetClass()(**kwargs)
        obj.sendBatchNotification = mock.Mock()
        return obj

    def getProcessExitedEvent(self, pname, gname, expected,
                                eventname='PROCESS_STATE_EXITED'):
        headers = {
            'ver': '3.0', 'poolserial': '7', 'len': '71',
            'server': 'supervisor', 'eventname': eventname,
            'serial': '7', 'pool': 'checkmailbatch',
        }
        payload = 'processname:%s groupname:%s from_state:RUNNING expected:%d \
pid:58597' % (pname, gname, expected)
        return (headers, payload)
        
    def getTick60Event(self):
        headers = {
            'ver': '3.0', 'poolserial': '5', 'len': '15',
            'server': 'supervisor', 'eventname': 'TICK_60',
            'serial': '5', 'pool': 'checkmailbatch',
        }
        payload = 'when:1279665240'
        return (headers, payload)
        
    def test_handleEvent_exit(self):
        monitor = self._makeOneMocked()
        hdrs, payload = self.getProcessExitedEvent('foo', 'bar', 0)
        monitor.handleEvent(hdrs, payload)
        unexpectedErrorMsg = repr(payload)
        self.assertEquals([unexpectedErrorMsg], monitor.getBatchMsgs())
        self.assertEquals('%s\n' % unexpectedErrorMsg, monitor.stderr.getvalue())

    def test_handleEvent_non_exit(self):
        monitor = self._makeOneMocked()
        hdrs, payload = self.getProcessExitedEvent('foo', 'bar', 0,
                                            eventname='PROCESS_STATE_FATAL')
        monitor.handleEvent(hdrs, payload)
        self.assertEquals([], monitor.getBatchMsgs())
        self.assertEquals('', monitor.stderr.getvalue())

    def test_handleEvent_tick_interval_expired(self):
        monitor = self._makeOneMocked()
        #Put msgs in batch
        hdrs, payload = self.getProcessExitedEvent('foo', 'bar', 0)
        monitor.handleEvent(hdrs, payload)
        hdrs, payload = self.getProcessExitedEvent('bark', 'dog', 0)
        monitor.handleEvent(hdrs, payload)
        self.assertEquals(2, len(monitor.getBatchMsgs()))
        #Time expired
        hdrs, payload = self.getTick60Event()
        monitor.handleEvent(hdrs, payload)
        
        #Test that batch messages are now gone
        self.assertEquals([], monitor.getBatchMsgs())
        #Test that email was sent
        self.assertEquals(1, monitor.sendBatchNotification.call_count)

    def test_handleEvent_tick_interval_not_expired(self):
        monitor = self._makeOneMocked(interval=3)
        hdrs, payload = self.getTick60Event()
        monitor.handleEvent(hdrs, payload)
        self.assertEquals(1.0, monitor.getBatchMinutes())
        monitor.handleEvent(hdrs, payload)
        self.assertEquals(2.0, monitor.getBatchMinutes())

if __name__ == '__main__':
    unittest.main()