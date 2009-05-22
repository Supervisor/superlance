import sys
import unittest
from StringIO import StringIO

class HTTPOkTests(unittest.TestCase):
    def _getTargetClass(self):
        from superlance.httpok import HTTPOk
        return HTTPOk
    
    def _makeOne(self, *opts):
        return self._getTargetClass()(*opts)

    def _makeOnePopulated(self, programs, any, response=None, exc=None,
                          gcore=None, coredir=None, eager=True):
        if response is None:
            response = DummyResponse()
        rpc = DummyRPCServer()
        sendmail = 'cat - > /dev/null'
        email = 'chrism@plope.com'
        url = 'http://foo/bar'
        timeout = 10
        status = '200'
        inbody = None
        gcore = gcore
        coredir = coredir
        prog = self._makeOne(rpc, programs, any, url, timeout, status,
                             inbody, email, sendmail, coredir, gcore, eager)
        prog.stdin = StringIO()
        prog.stdout = StringIO()
        prog.stderr = StringIO()
        prog.connclass = make_connection(response, exc=exc)
        return prog

    def test_listProcesses_no_programs(self):
        programs = []
        any = None
        prog = self._makeOnePopulated(programs, any)
        specs = list(prog.listProcesses())
        self.assertEqual(len(specs), 0)

    def test_listProcesses_w_RUNNING_programs_default_state(self):
        programs = ['foo']
        any = None
        prog = self._makeOnePopulated(programs, any)
        specs = list(prog.listProcesses())
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0],
                         DummySupervisorRPCNamespace.all_process_info[0])

    def test_listProcesses_w_nonRUNNING_programs_default_state(self):
        programs = ['bar']
        any = None
        prog = self._makeOnePopulated(programs, any)
        specs = list(prog.listProcesses())
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0],
                         DummySupervisorRPCNamespace.all_process_info[1])

    def test_listProcesses_w_nonRUNNING_programs_RUNNING_state(self):
        programs = ['bar']
        any = None
        prog = self._makeOnePopulated(programs, any)
        specs = list(prog.listProcesses(ProcessStates.RUNNING))
        self.assertEqual(len(specs), 0, (prog.programs, specs))

    def test_runforever_eager_notatick(self):
        programs = {'foo':0, 'bar':0, 'baz_01':0 }
        groups = {}
        any = None
        prog = self._makeOnePopulated(programs, any)
        prog.stdin.write('eventname:NOTATICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        self.assertEqual(prog.stderr.getvalue(), '')

    def test_runforever_eager_error_on_request_some(self):
        programs = ['foo', 'bar', 'baz_01', 'notexisting']
        any = None
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        #self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0],
                         ("Restarting selected processes ['foo', 'bar', "
                          "'baz_01', 'notexisting']")
                         )
        self.assertEqual(lines[1], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[2], 'foo restarted')
        self.assertEqual(lines[3], 'bar not in RUNNING state, NOT restarting')
        self.assertEqual(lines[4],
                         'baz:baz_01 not in RUNNING state, NOT restarting')
        self.assertEqual(lines[5],
          "Programs not restarted because they did not exist: ['notexisting']")
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 12)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok for http://foo/bar: bad status returned')

    def test_runforever_eager_error_on_request_any(self):
        programs = []
        any = True
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        #self.assertEqual(len(lines), 6)
        self.assertEqual(lines[0], 'Restarting all running processes')
        self.assertEqual(lines[1], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[2], 'foo restarted')
        self.assertEqual(lines[3], 'bar not in RUNNING state, NOT restarting')
        self.assertEqual(lines[4],
                         'baz:baz_01 not in RUNNING state, NOT restarting')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 11)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok for http://foo/bar: bad status returned')

    def test_runforever_eager_error_on_process_stop(self):
        programs = ['FAILED']
        any = False
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.rpc.supervisor.all_process_info = _FAIL
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        #self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], "Restarting selected processes ['FAILED']")
        self.assertEqual(lines[1], 'foo:FAILED is in RUNNING state, restarting')
        self.assertEqual(lines[2],
                    "Failed to stop process foo:FAILED: <Fault 30: 'FAILED'>")
        self.assertEqual(lines[3], 'foo:FAILED restarted')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 10)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok for http://foo/bar: bad status returned')

    def test_runforever_eager_error_on_process_start(self):
        programs = ['SPAWN_ERROR']
        any = False
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.rpc.supervisor.all_process_info = _FAIL
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        #self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0],
                         "Restarting selected processes ['SPAWN_ERROR']")
        self.assertEqual(lines[1],
                         'foo:SPAWN_ERROR is in RUNNING state, restarting')
        self.assertEqual(lines[2],
           "Failed to start process foo:SPAWN_ERROR: <Fault 50: 'SPAWN_ERROR'>")
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 9)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok for http://foo/bar: bad status returned')

    def test_runforever_eager_gcore(self):
        programs = ['foo', 'bar', 'baz_01', 'notexisting']
        any = None
        prog = self._makeOnePopulated(programs, any, exc=True, gcore="true",
                                      coredir="/tmp")
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertEqual(lines[0],
                         ("Restarting selected processes ['foo', 'bar', "
                          "'baz_01', 'notexisting']")
                         )
        self.assertEqual(lines[1], 'gcore output for foo:')
        self.assertEqual(lines[2], '')
        self.assertEqual(lines[3], ' ')
        self.assertEqual(lines[4], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[5], 'foo restarted')
        self.assertEqual(lines[6], 'bar not in RUNNING state, NOT restarting')
        self.assertEqual(lines[7],
                         'baz:baz_01 not in RUNNING state, NOT restarting')
        self.assertEqual(lines[8],
          "Programs not restarted because they did not exist: ['notexisting']")
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 15)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok for http://foo/bar: bad status returned')

    def test_runforever_not_eager_none_running(self):
        programs = ['bar', 'baz_01']
        any = None
        prog = self._makeOnePopulated(programs, any, exc=True, gcore="true",
                                      coredir="/tmp", eager=False)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = filter(None, prog.stderr.getvalue().split('\n'))
        self.assertEqual(len(lines), 0, lines)
        self.failIf('mailed' in prog.__dict__)

    def test_runforever_not_eager_running(self):
        programs = ['foo', 'bar']
        any = None
        prog = self._makeOnePopulated(programs, any, exc=True, eager=False)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = filter(None, prog.stderr.getvalue().split('\n'))
        self.assertEqual(lines[0],
                         ("Restarting selected processes ['foo', 'bar']")
                         )
        self.assertEqual(lines[1], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[2], 'foo restarted')
        self.assertEqual(lines[3], 'bar not in RUNNING state, NOT restarting')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 10)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok for http://foo/bar: bad status returned')

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
        programs = {'foo':0, 'bar':0, 'baz_01':0 }
        groups = {}
        any = None
        prog = self._makeOnePopulated(programs, any)
        prog.stdin.write('eventname:PROCESS_STATE len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        self.assertEqual(prog.stderr.getvalue(), 'non-exited event\n')

    def test_runforever_expected_exit(self):
        programs = ['foo']
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
        programs = ['foo']
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
        self.assertEqual(lines[0], 'unexpected exit, mailing')
        self.assertEqual(lines[1], 'Mailed:')
        self.assertEqual(lines[2], '')
        self.assertEqual(lines[3], 'To: chrism@plope.com')
        self.failUnless('Subject: [foo]: foo crashed at' in lines[4])
        self.assertEqual(lines[5], '')
        self.failUnless(
            'Process foo in group bar exited unexpectedly' in lines[6])
        import os
        mail = open(os.path.join(self.tempdir, 'email.log'), 'r').read()
        self.failUnless(
            'Process foo in group bar exited unexpectedly' in mail)


class MemmonTests(unittest.TestCase):
    def _getTargetClass(self):
        from supervisor.memmon import Memmon
        return Memmon
    
    def _makeOne(self, *opts):
        return self._getTargetClass()(*opts)

    def _makeOnePopulated(self, programs, groups, any):
        from supervisor.tests.base import DummyRPCServer
        rpc = DummyRPCServer()
        sendmail = 'cat - > /dev/null'
        email = 'chrism@plope.com'
        memmon = self._makeOne(programs, groups, any, sendmail, email, rpc)
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
                         'Subject: memmon: process baz:baz_01 restarted')
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
          'Subject: memmon: process foo:foo restarted')
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
                         'Subject: memmon: process baz:baz_01 restarted')
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
          'Subject: memmon: failed to stop process BAD_NAME:BAD_NAME, exiting')
        self.assertEqual(mailed[2], '')
        self.failUnless(mailed[3].startswith('Failed'))


def make_connection(response, exc=None):
    class TestConnection:
        def __init__(self, hostport):
            self.hostport = hostport

        def request(self, method, path):
            if exc:
                raise ValueError('foo')
            self.method = method
            self.path = path

        def getresponse(self):
            return response

    return TestConnection

class DummyResponse:
    status = 200
    reason = 'OK'
    body = 'OK'
    def read(self):
        return self.body

class DummyRPCServer:
    def __init__(self):
        self.supervisor = DummySupervisorRPCNamespace()
        self.system = DummySystemRPCNamespace()

class DummySystemRPCNamespace:
    pass

import time
from supervisor.process import ProcessStates

_NOW = time.time()

_FAIL = [ {
        'name':'FAILED',
        'group':'foo',
        'pid':11,
        'state':ProcessStates.RUNNING,
        'statename':'RUNNING',
        'start':_NOW - 100,
        'stop':0,
        'spawnerr':'',
        'now':_NOW,
        'description':'foo description',
        },
{
        'name':'SPAWN_ERROR',
        'group':'foo',
        'pid':11,
        'state':ProcessStates.RUNNING,
        'statename':'RUNNING',
        'start':_NOW - 100,
        'stop':0,
        'spawnerr':'',
        'now':_NOW,
        'description':'foo description',
        },]

class DummySupervisorRPCNamespace:
    _restartable = True
    _restarted = False
    _shutdown = False
    _readlog_error = False


    all_process_info = [
        {
        'name':'foo',
        'group':'foo',
        'pid':11,
        'state':ProcessStates.RUNNING,
        'statename':'RUNNING',
        'start':_NOW - 100,
        'stop':0,
        'spawnerr':'',
        'now':_NOW,
        'description':'foo description',
        },
        {
        'name':'bar',
        'group':'bar',
        'pid':12,
        'state':ProcessStates.FATAL,
        'statename':'FATAL',
        'start':_NOW - 100,
        'stop':_NOW - 50,
        'spawnerr':'screwed',
        'now':_NOW,
        'description':'bar description',
        },
        {
        'name':'baz_01',
        'group':'baz',
        'pid':12,
        'state':ProcessStates.STOPPED,
        'statename':'STOPPED',
        'start':_NOW - 100,
        'stop':_NOW - 25,
        'spawnerr':'',
        'now':_NOW,
        'description':'baz description',
        },
        ]

    def getAllProcessInfo(self):
        return self.all_process_info

    def startProcess(self, name):
        from supervisor import xmlrpc
        from xmlrpclib import Fault
        if name.endswith('SPAWN_ERROR'):
            raise Fault(xmlrpc.Faults.SPAWN_ERROR, 'SPAWN_ERROR')
        return True

    def stopProcess(self, name):
        from supervisor import xmlrpc
        from xmlrpclib import Fault
        if name.endswith('FAILED'):
            raise Fault(xmlrpc.Faults.FAILED, 'FAILED')
        return True
    

def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
