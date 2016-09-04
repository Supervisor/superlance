import unittest
from superlance.compat import StringIO
import re

class CrashMailTests(unittest.TestCase):
    def _getTargetClass(self):
        from superlance.crashmail import CrashMail
        return CrashMail

    def _makeOne(self, *opts):
        return self._getTargetClass()(*opts)

    def setUp(self):
        import tempfile
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tempdir)

    def _makeOnePopulated(self, programs, any, response=None):
        import os
        sendmail = 'cat - > %s' % os.path.join(self.tempdir, 'email.log')
        email = 'chrism@plope.com'
        header = '[foo]'
        prog = self._makeOne(programs, any, email, sendmail, header)
        prog.stdin = StringIO()
        prog.stdout = StringIO()
        prog.stderr = StringIO()
        return prog

    def test_runforever_not_process_state_exited(self):
        programs = []
        any = None
        prog = self._makeOnePopulated(programs, any)
        prog.stdin.write('eventname:PROCESS_STATE len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        self.assertEqual(prog.stderr.getvalue(), 'non-exited event\n')

    def test_runforever_expected_exit(self):
        programs = [re.compile('foo')]
        any = None
        prog = self._makeOnePopulated(programs, any)
        payload=('expected:1 processname:foo groupname:bar '
                 'from_state:RUNNING pid:1')
        prog.stdin.write(
            'eventname:PROCESS_STATE_EXITED len:%s\n' % len(payload))
        prog.stdin.write(payload)
        prog.stdin.seek(0)
        prog.runforever(test=True)
        self.assertEqual(prog.stderr.getvalue(), 'expected exit\n')

    def test_runforever_unexpected_exit(self):
        programs = [re.compile('bar:foo')]
        any = None
        prog = self._makeOnePopulated(programs, any)
        payload=('expected:0 processname:foo groupname:bar '
                 'from_state:RUNNING pid:1')
        prog.stdin.write(
            'eventname:PROCESS_STATE_EXITED len:%s\n' % len(payload))
        prog.stdin.write(payload)
        prog.stdin.seek(0)
        prog.runforever(test=True)
        output = prog.stderr.getvalue()
        lines = output.split('\n')

        self.assertEqual(lines[1], 'unexpected exit, mailing')
        self.assertEqual(lines[2], 'Mailed:')
        self.assertEqual(lines[3], '')
        self.assertEqual(lines[4], 'To: chrism@plope.com')
        self.assertTrue('Subject: [foo]: foo crashed at' in lines[5])
        self.assertEqual(lines[6], '')
        self.assertTrue(
            'Process foo in group bar exited unexpectedly' in lines[7])
        import os
        f = open(os.path.join(self.tempdir, 'email.log'), 'r')
        mail = f.read()
        f.close()
        self.assertTrue(
            'Process foo in group bar exited unexpectedly' in mail)

    def test_runforever_unexpected_exit_group(self):
        programs = [re.compile('bar:*')]
        any = None
        prog = self._makeOnePopulated(programs, any)
        payload=('expected:0 processname:foo groupname:bar '
                 'from_state:RUNNING pid:1')
        prog.stdin.write(
            'eventname:PROCESS_STATE_EXITED len:%s\n' % len(payload))
        prog.stdin.write(payload)
        prog.stdin.seek(0)
        prog.runforever(test=True)
        output = prog.stderr.getvalue()
        lines = output.split('\n')

        self.assertEqual(lines[1], 'unexpected exit, mailing')

    def test_runforever_unexpected_exit_ignored(self):
        programs = [re.compile('notfoo')]
        any = None
        prog = self._makeOnePopulated(programs, any)
        payload=('expected:0 processname:foo groupname:bar '
                 'from_state:RUNNING pid:1')
        prog.stdin.write(
            'eventname:PROCESS_STATE_EXITED len:%s\n' % len(payload))
        prog.stdin.write(payload)
        prog.stdin.seek(0)
        prog.runforever(test=True)
        output = prog.stderr.getvalue()
        lines = output.split('\n')

        self.assertTrue('ignoring [foo]: foo crashed ' in lines[1])

if __name__ == '__main__':
    unittest.main()
