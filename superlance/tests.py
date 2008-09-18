import sys
import unittest
from StringIO import StringIO

class HTTPOkTests(unittest.TestCase):
    def _getTargetClass(self):
        from superlance.httpok import HTTPOk
        return HTTPOk
    
    def _makeOne(self, *opts):
        return self._getTargetClass()(*opts)

    def _makeOnePopulated(self, programs, any, response=None, exc=None):
        if response is None:
            response = DummyResponse()
        rpc = DummyRPCServer()
        sendmail = 'cat - > /dev/null'
        email = 'chrism@plope.com'
        url = 'http://foo/bar'
        timeout = 10
        status = '200'
        inbody = None
        prog = self._makeOne(rpc, programs, any, url, timeout, status,
                             inbody, email, sendmail)
        prog.stdin = StringIO()
        prog.stdout = StringIO()
        prog.stderr = StringIO()
        prog.connclass = make_connection(response, exc=exc)
        return prog
        
    def test_runforever_notatick(self):
        programs = {'foo':0, 'bar':0, 'baz_01':0 }
        groups = {}
        any = None
        prog = self._makeOnePopulated(programs, any)
        prog.stdin.write('eventname:NOTATICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        self.assertEqual(prog.stderr.getvalue(), '')

    def test_runforever_error_on_request_some(self):
        programs = ['foo', 'bar', 'baz_01', 'notexisting']
        any = None
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 7)
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

    def test_runforever_error_on_request_any(self):
        programs = []
        any = True
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 6)
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

    def test_runforever_error_on_process_stop(self):
        programs = ['FAILED']
        any = False
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.rpc.supervisor.all_process_info = _FAIL
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 5)
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

    def test_runforever_error_on_process_start(self):
        programs = ['SPAWN_ERROR']
        any = False
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.rpc.supervisor.all_process_info = _FAIL
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertEqual(len(lines), 4)
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
