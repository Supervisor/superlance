import unittest

from .test_crashmailbatch import CrashMailBatchTests

class CrashSMSTests(CrashMailBatchTests):
    subject = None
    unexpected_err_msg = '[bar:foo](58597) exited unexpectedly'

    def _get_target_class(self):
        from superlance.crashsms import CrashSMS
        return CrashSMS

    def test_sets_default_subject_when_None(self):
        crash = self._make_one_mocked(subject=None)
        self.assertEqual(crash.subject, self.subject)

if __name__ == '__main__':
    unittest.main()
