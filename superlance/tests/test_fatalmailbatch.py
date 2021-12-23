import unittest
try: # pragma: no cover
    from unittest.mock import Mock
except ImportError: # pragma: no cover
    from mock import Mock
from superlance.compat import StringIO

class FatalMailBatchTests(unittest.TestCase):
    from_email = 'testFrom@blah.com'
    to_emails = ('testTo@blah.com')
    subject = 'Test Alert'
    unexpected_err_msg = 'Process bar:foo failed to start too many times'

    def _get_target_class(self):
        from superlance.fatalmailbatch import FatalMailBatch
        return FatalMailBatch

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

    def get_process_fatal_event(self, pname, gname):
        headers = {
            'ver': '3.0', 'poolserial': '7', 'len': '71',
            'server': 'supervisor', 'eventname': 'PROCESS_STATE_FATAL',
            'serial': '7', 'pool': 'checkmailbatch',
        }
        payload = 'processname:%s groupname:%s from_state:BACKOFF' \
                % (pname, gname)
        return (headers, payload)

    def test_get_process_state_change_msg(self):
        crash = self._make_one_mocked()
        hdrs, payload = self.get_process_fatal_event('foo', 'bar')
        msg = crash.get_process_state_change_msg(hdrs, payload)
        self.assertTrue(self.unexpected_err_msg in msg)

    def test_sets_default_subject_when_None(self):
        crash = self._make_one_mocked(subject=None) # see issue #109
        self.assertEqual(crash.subject, "Fatal start alert from supervisord")

if __name__ == '__main__':
    unittest.main()
