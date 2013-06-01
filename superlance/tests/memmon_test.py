import sys
import unittest
from StringIO import StringIO
from superlance.tests.dummy import *
from superlance.memmon import seconds_size

class MemmonTests(unittest.TestCase):
    def _getTargetClass(self):
        from superlance.memmon import Memmon
        return Memmon

    def _makeOne(self, *opts):
        return self._getTargetClass()(*opts)

    def _makeOnePopulated(self, programs, groups, any):
        rpc = DummyRPCServer()
        sendmail = 'cat - > /dev/null'
        email = 'chrism@plope.com'
        name = 'test'
        uptime_limit = 2000
        memmon = self._makeOne(programs, groups, any, sendmail, email, uptime_limit, name, rpc)
        memmon.stdin = StringIO()
        memmon.stdout = StringIO()
        memmon.stderr = StringIO()
        memmon.pscommand = 'echo 22%s'
        return memmon

    def test_runforever_notatick(self):
        programs = {'foo':0, 'bar':0, 'baz_01':0 }
        groups = {}
        any = None
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.stdin.write('eventname:NOTATICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        self.assertEqual(memmon.stderr.getvalue(), '')

    def test_runforever_tick_programs(self):
        programs = {'foo':0, 'bar':0, 'baz_01':0 }
        groups = {}
        any = None
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        lines = memmon.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0], 'Checking programs foo=0, bar=0, baz_01=0')
        self.assertEqual(lines[1], 'RSS of foo:foo is 2264064')
        self.assertEqual(lines[2], 'Restarting foo:foo')
        self.assertEqual(lines[3], 'RSS of bar:bar is 2265088')
        self.assertEqual(lines[4], 'Restarting bar:bar')
        self.assertEqual(lines[5], 'RSS of baz:baz_01 is 2265088')
        self.assertEqual(lines[6], 'Restarting baz:baz_01')
        self.assertEqual(lines[7], '')
        mailed = memmon.mailed.split('\n')
        self.assertEqual(len(mailed), 4)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                         'Subject: memmon [test]: process baz:baz_01 restarted')
        self.assertEqual(mailed[2], '')
        self.failUnless(mailed[3].startswith('memmon.py restarted'))

    def test_runforever_tick_groups(self):
        programs = {}
        groups = {'foo':0}
        any = None
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        lines = memmon.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], 'Checking groups foo=0')
        self.assertEqual(lines[1], 'RSS of foo:foo is 2264064')
        self.assertEqual(lines[2], 'Restarting foo:foo')
        self.assertEqual(lines[3], '')
        mailed = memmon.mailed.split('\n')
        self.assertEqual(len(mailed), 4)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
          'Subject: memmon [test]: process foo:foo restarted')
        self.assertEqual(mailed[2], '')
        self.failUnless(mailed[3].startswith('memmon.py restarted'))

    def test_runforever_tick_any(self):
        programs = {}
        groups = {}
        any = 0
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        lines = memmon.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0], 'Checking any=0')
        self.assertEqual(lines[1], 'RSS of foo:foo is 2264064')
        self.assertEqual(lines[2], 'Restarting foo:foo')
        self.assertEqual(lines[3], 'RSS of bar:bar is 2265088')
        self.assertEqual(lines[4], 'Restarting bar:bar')
        self.assertEqual(lines[5], 'RSS of baz:baz_01 is 2265088')
        self.assertEqual(lines[6], 'Restarting baz:baz_01')
        self.assertEqual(lines[7], '')
        mailed = memmon.mailed.split('\n')
        self.assertEqual(len(mailed), 4)

    def test_runforever_tick_programs_and_groups(self):
        programs = {'baz_01':0}
        groups = {'foo':0}
        any = None
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        lines = memmon.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], 'Checking programs baz_01=0')
        self.assertEqual(lines[1], 'Checking groups foo=0')
        self.assertEqual(lines[2], 'RSS of foo:foo is 2264064')
        self.assertEqual(lines[3], 'Restarting foo:foo')
        self.assertEqual(lines[4], 'RSS of baz:baz_01 is 2265088')
        self.assertEqual(lines[5], 'Restarting baz:baz_01')
        self.assertEqual(lines[6], '')
        mailed = memmon.mailed.split('\n')
        self.assertEqual(len(mailed), 4)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                         'Subject: memmon [test]: process baz:baz_01 restarted')
        self.assertEqual(mailed[2], '')
        self.failUnless(mailed[3].startswith('memmon.py restarted'))

    def test_runforever_tick_programs_norestart(self):
        programs = {'foo': sys.maxint}
        groups = {}
        any = None
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        lines = memmon.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], 'Checking programs foo=%s' % sys.maxint)
        self.assertEqual(lines[1], 'RSS of foo:foo is 2264064')
        self.assertEqual(lines[2], '')
        self.assertEqual(memmon.mailed, False)

    def test_stopprocess_fault_tick_programs_norestart(self):
        programs = {'foo': sys.maxint}
        groups = {}
        any = None
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        lines = memmon.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], 'Checking programs foo=%s' % sys.maxint)
        self.assertEqual(lines[1], 'RSS of foo:foo is 2264064')
        self.assertEqual(lines[2], '')
        self.assertEqual(memmon.mailed, False)

    def test_stopprocess_fails_to_stop(self):
        programs = {'BAD_NAME': 0}
        groups = {}
        any = None
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        from supervisor.process import ProcessStates
        memmon.rpc.supervisor.all_process_info =  [ {
            'name':'BAD_NAME',
            'group':'BAD_NAME',
            'pid':11,
            'state':ProcessStates.RUNNING,
            'statename':'RUNNING',
            'start':0,
            'stop':0,
            'spawnerr':'',
            'now':0,
            'description':'BAD_NAME description',
             } ]
        import xmlrpclib
        self.assertRaises(xmlrpclib.Fault, memmon.runforever, True)
        lines = memmon.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], 'Checking programs BAD_NAME=%s' % 0)
        self.assertEqual(lines[1], 'RSS of BAD_NAME:BAD_NAME is 2264064')
        self.assertEqual(lines[2], 'Restarting BAD_NAME:BAD_NAME')
        self.failUnless(lines[3].startswith('Failed'))
        mailed = memmon.mailed.split('\n')
        self.assertEqual(len(mailed), 4)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
          'Subject: memmon [test]: failed to stop process BAD_NAME:BAD_NAME, exiting')
        self.assertEqual(mailed[2], '')
        self.failUnless(mailed[3].startswith('Failed'))

    def test_subject_no_name(self):
        """set the name to None to check if subject
        stays `memmon:...` instead `memmon [<name>]:...`
        """
        programs = {}
        groups = {}
        any = 0
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.memmonName = None
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)

        mailed = memmon.mailed.split('\n')
        self.assertEqual(mailed[1],
          'Subject: memmon: process baz:baz_01 restarted')

    def test_parse_uptime(self):
        """test parsing of time parameter for uptime
        """
        self.assertEqual(seconds_size('1'), 1, 'default is seconds')
        self.assertEqual(seconds_size('1s'), 1, 'seconds suffix is allowed, too')
        self.assertEqual(seconds_size('2m'), 120)
        self.assertEqual(seconds_size('3h'), 10800)
        self.assertEqual(seconds_size('1d'), 86400)
        self.assertRaises(ValueError, seconds_size, '1y')

    def test_uptime_short_email(self):
        """in case an email is provided and the restarted process' uptime
        is shorter than our uptime_limit we do send an email
        """
        programs = {'foo':0}
        groups = {}
        any = None
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.email_uptime_limit = 101
        
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        self.assertTrue(memmon.mailed, 'email has been sent')
        
        #in case uptime == limit, we send an email too
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.email_uptime_limit = 100
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        self.assertTrue(memmon.mailed, 'email has been sent')
        
             
        
    def test_uptime_long_no_email(self):
        """in case an email is provided and the restarted process' uptime
        is longer than our uptime_limit we do not send an email
        """
        programs = {'foo':0}
        groups = {}
        any = None
        memmon = self._makeOnePopulated(programs, groups, any)
        memmon.email_uptime_limit = 99
        
        memmon.stdin.write('eventname:TICK len:0\n')
        memmon.stdin.seek(0)
        memmon.runforever(test=True)
        self.assertFalse(memmon.mailed, 'no email should be sent because uptime is above limit')
              
        
        
if __name__ == '__main__':
    unittest.main()