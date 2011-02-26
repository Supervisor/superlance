import unittest
import mock
import time
from StringIO import StringIO

from crashmailbatch_test import CrashMailBatchTests

class CrashSMSBatchTests(CrashMailBatchTests):
    subject = 'None'
    unexpectedErrorMsg = '[bar:foo](58597) exited unexpectedly'

    def _getTargetClass(self):
        from superlance.crashsms import CrashSMS
        return CrashSMS

if __name__ == '__main__':
    unittest.main()