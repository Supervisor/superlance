import unittest
try: # pragma: no cover
    from unittest.mock import Mock
except ImportError: # pragma: no cover
    from mock import Mock
from superlance.compat import StringIO

class CrashMailBatchTests(unittest.TestCase):
    from_email = 'testFrom@blah.com'
    to_emails = ('testTo@blah.com')
    subject = 'Test Alert'
    unexpected_err_msg = 'Process bar:foo (pid 58597) died unexpectedly'

    def _get_target_class(self):
        from superlance.crashmailbatch import CrashMailBatch
        return CrashMailBatch

    def _make_one_mocked(self, **kwargs):
        kwargs['stdin'] = StringIO()
        kwargs['stdout'] = StringIO()
        kwargs['stderr'] = StringIO()
        kwargs['from_email'] = kwargs.get('from_email', self.from_email)
        kwargs['to_emails'] = kwargs.get('to_emails', self.to_emails)
        kwargs['subject'] = kwargs.get('subject', self.subject)

        obj = self._get_target_class()(**kwargs)
        obj.send_email = Mock()
        return obj

    def get_process_exited_event(self, pname, gname, expected):
        headers = {
            'ver': '3.0', 'poolserial': '7', 'len': '71',
            'server': 'supervisor', 'eventname': 'PROCESS_STATE_EXITED',
            'serial': '7', 'pool': 'checkmailbatch',
        }
        payload = 'processname:%s groupname:%s from_state:RUNNING expected:%d \
pid:58597' % (pname, gname, expected)
        return (headers, payload)

    def test_get_process_state_change_msg_expected(self):
        crash = self._make_one_mocked()
        hdrs, payload = self.get_process_exited_event('foo', 'bar', 1)
        self.assertEqual(None, crash.get_process_state_change_msg(hdrs, payload))

    def test_get_process_state_change_msg_unexpected(self):
        crash = self._make_one_mocked()
        hdrs, payload = self.get_process_exited_event('foo', 'bar', 0)
        msg = crash.get_process_state_change_msg(hdrs, payload)
        self.assertTrue(self.unexpected_err_msg in msg)

    def test_handle_event_exit_expected(self):
        crash = self._make_one_mocked()
        hdrs, payload = self.get_process_exited_event('foo', 'bar', 1)
        crash.handle_event(hdrs, payload)
        self.assertEqual([], crash.get_batch_msgs())
        self.assertEqual('', crash.stderr.getvalue())

    def test_handle_event_exit_unexpected(self):
        crash = self._make_one_mocked()
        hdrs, payload = self.get_process_exited_event('foo', 'bar', 0)
        crash.handle_event(hdrs, payload)
        msgs = crash.get_batch_msgs()
        self.assertEqual(1, len(msgs))
        self.assertTrue(self.unexpected_err_msg in msgs[0])
        self.assertTrue(self.unexpected_err_msg in crash.stderr.getvalue())

    def test_sets_default_subject_when_None(self):
        crash = self._make_one_mocked(subject=None) # see issue #109
        self.assertEqual(crash.subject, "Crash alert from supervisord")

if __name__ == '__main__':
    unittest.main()
