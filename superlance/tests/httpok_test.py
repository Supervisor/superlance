import socket
import time
import unittest
import mock
from superlance.compat import StringIO
from supervisor.process import ProcessStates
from superlance.tests.dummy import DummyResponse
from superlance.tests.dummy import DummyRPCServer
from superlance.tests.dummy import DummySupervisorRPCNamespace

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

def make_connection(response, exc=None):
    class TestConnection:
        def __init__(self, hostport):
            self.hostport = hostport

        def request(self, method, path, headers):
            if exc:
                if exc == True:
                    raise ValueError('foo')
                else:
                    raise exc.pop()
            self.method = method
            self.path = path
            self.headers = headers

        def getresponse(self):
            return response

    return TestConnection

class HTTPOkTests(unittest.TestCase):
    def _getTargetClass(self):
        from superlance.httpok import HTTPOk
        return HTTPOk

    def _makeOne(self, *opts):
        return self._getTargetClass()(*opts)

    def _makeOnePopulated(self, programs, any, response=None, exc=None,
            gcore=None, coredir=None, eager=True, restart_threshold=3,
            restart_timespan=60, ext_service=None, restart_string=None):
        if response is None:
            response = DummyResponse()
        rpc = DummyRPCServer()
        sendmail = 'cat - > /dev/null'
        email = 'chrism@plope.com'
        url = 'http://foo/bar'
        timeout = 10
        retry_time = 0
        status = '200'
        inbody = None
        gcore = gcore
        coredir = coredir
        prog = self._makeOne(rpc, programs, any, url, timeout, status,
            inbody, email, sendmail, coredir, gcore, eager, retry_time,
            restart_threshold, restart_timespan, ext_service, restart_string)
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

    def test_restart_counter(self):
        programs = ['bar']
        any = None
        prog = self._makeOnePopulated(programs, any)
        specs = list(prog.listProcesses())
        write = lambda x: prog.stderr.write(x + '\n')
        for i in xrange(4):
            prog.restartCounter(specs[0], write)
        lines = prog.stderr.getvalue().strip().split('\n')
        self.assertEqual(lines[0], 'bar restart is approved')
        self.assertEqual(lines[1], 'bar restart attempt: 2')
        self.assertEqual(lines[2], 'bar restart attempt: 3')
        self.assertEqual(lines[3], ('Not restarting bar anymore. Restarted 3 '
                                    'times'))

        
    def test_restart_threshold_zero(self):
        programs = ['bar']
        any = None
        prog = self._makeOnePopulated(programs, any, restart_threshold=0)
        specs = list(prog.listProcesses())
        write = lambda x: prog.stderr.write(x + '\n')
        for i in xrange(20):
            prog.restartCounter(specs[0], write)
        lines = prog.stderr.getvalue().strip().split('\n')
        self.assertEqual(lines[0], 'bar restart is approved')
        for i in xrange(1, 20):
            self.assertEqual(lines[i], ('bar in restart loop, attempt: %s'
                                        % (i + 1)))

    def test_restart_external_script(self):
        programs = ['foo']
        any = None
        prog = self._makeOnePopulated(programs, any, exc=True,
            ext_service=mock.MagicMock())
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertEqual(lines[0],
                         "Restarting selected processes ['foo']"
                         )
        self.assertEqual(lines[1], 'foo restart is approved')
        self.assertEqual(lines[2], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[3], 'foo restarted')

    def test_restart_string(self):
        programs = ['foo']
        any = None
        response = DummyResponse()
        response.body = 'boo'
        prog = self._makeOnePopulated(programs, any, response=response,
                                      restart_string=['boo'])
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertEqual(lines[0],
                         "Restarting selected processes ['foo']"
                         )
        self.assertEqual(lines[1], 'foo restart is approved')
        self.assertEqual(lines[2], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[3], 'foo restarted')
        self.assertEqual(lines[7], ('Subject: httpok for http://foo/bar: '
                                    'restart string in body'))
        
    def test_clean_counters(self):
        programs = ['bar']
        any = None
        prog = self._makeOnePopulated(programs, any)
        specs = list(prog.listProcesses())
        write = lambda x: prog.stderr.write(x + '\n')
        for i in xrange(3):
            prog.restartCounter(specs[0], write)
        self.assertEqual(prog.counter[specs[0]['name']]['counter'], 3)
        prog.cleanCounters()
        # Ensure that the counters don't clean up due to restart_time
        self.assertEqual(prog.counter[specs[0]['name']]['counter'], 3)
        prog.counter[specs[0]['name']]['restart_time'] = 0
        prog.cleanCounters()
        self.assertEqual(prog.counter[specs[0]['name']]['counter'], 0)


    def test_runforever_eager_notatick(self):
        programs = {'foo':0, 'bar':0, 'baz_01':0 }
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
        self.assertEqual(lines[1], 'foo restart is approved')
        self.assertEqual(lines[2], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[3], 'foo restarted')
        self.assertEqual(lines[4], 'bar restart is approved')
        self.assertEqual(lines[5], 'bar not in RUNNING state, NOT restarting')
        self.assertEqual(lines[6], 'baz_01 restart is approved')
        self.assertEqual(lines[7],
                         'baz:baz_01 not in RUNNING state, NOT restarting')
        self.assertEqual(lines[8],
          "Programs not restarted because they did not exist: ['notexisting']")
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 15)
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
        self.assertEqual(lines[1], 'foo restart is approved')
        self.assertEqual(lines[2], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[3], 'foo restarted')
        self.assertEqual(lines[4], 'bar restart is approved')
        self.assertEqual(lines[5], 'bar not in RUNNING state, NOT restarting')
        self.assertEqual(lines[6], 'baz_01 restart is approved')
        self.assertEqual(lines[7],
                         'baz:baz_01 not in RUNNING state, NOT restarting')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 14)
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
        self.assertEqual(lines[1], "FAILED restart is approved")
        self.assertEqual(lines[2], 'foo:FAILED is in RUNNING state, restarting')
        self.assertEqual(lines[3],
                    "Failed to stop process foo:FAILED: <Fault 30: 'FAILED'>")
        self.assertEqual(lines[4], 'foo:FAILED restarted')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 11)
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
                         'SPAWN_ERROR restart is approved')
        self.assertEqual(lines[2],
                         'foo:SPAWN_ERROR is in RUNNING state, restarting')
        self.assertEqual(lines[3],
           "Failed to start process foo:SPAWN_ERROR: <Fault 50: 'SPAWN_ERROR'>")
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 10)
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
        self.assertEqual(lines[1], 'foo restart is approved')
        self.assertEqual(lines[2], 'gcore output for foo:')
        self.assertEqual(lines[3], '')
        self.assertEqual(lines[4], ' ')
        self.assertEqual(lines[5], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[6], 'foo restarted')
        self.assertEqual(lines[7], 'bar restart is approved')
        self.assertEqual(lines[8], 'bar not in RUNNING state, NOT restarting')
        self.assertEqual(lines[9], 'baz_01 restart is approved')
        self.assertEqual(lines[10],
                         'baz:baz_01 not in RUNNING state, NOT restarting')
        self.assertEqual(lines[11],
          "Programs not restarted because they did not exist: ['notexisting']")
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 18)
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
        lines = [x for x in prog.stderr.getvalue().split('\n') if x]
        self.assertEqual(len(lines), 0, lines)
        self.assertFalse('mailed' in prog.__dict__)

    def test_runforever_not_eager_running(self):
        programs = ['foo', 'bar']
        any = None
        prog = self._makeOnePopulated(programs, any, exc=True, eager=False)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = [x for x in prog.stderr.getvalue().split('\n') if x]
        self.assertEqual(lines[0],
                         ("Restarting selected processes ['foo', 'bar']")
                         )
        self.assertEqual(lines[1], 'foo restart is approved')
        self.assertEqual(lines[2], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[3], 'foo restarted')
        self.assertEqual(lines[4], 'bar restart is approved')
        self.assertEqual(lines[5], 'bar not in RUNNING state, NOT restarting')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 12)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok for http://foo/bar: bad status returned')

    def test_runforever_honor_timeout_on_connrefused(self):
        programs = ['foo', 'bar']
        any = None
        error = socket.error()
        error.errno = 111
        prog = self._makeOnePopulated(programs, any, exc=[error], eager=False)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        self.assertEqual(prog.stderr.getvalue(), '')
        self.assertEqual(prog.stdout.getvalue(), 'READY\nRESULT 2\nOK')

    def test_runforever_connrefused_error(self):
        programs = ['foo', 'bar']
        any = None
        error = socket.error()
        error.errno = 111
        prog = self._makeOnePopulated(programs, any,
            exc=[error for x in range(100)], eager=False)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = [x for x in prog.stderr.getvalue().split('\n') if x]
        self.assertEqual(lines[0],
                         ("Restarting selected processes ['foo', 'bar']")
                         )
        self.assertEqual(lines[1], 'foo restart is approved')
        self.assertEqual(lines[2], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[3], 'foo restarted')
        self.assertEqual(lines[4], 'bar restart is approved')
        self.assertEqual(lines[5], 'bar not in RUNNING state, NOT restarting')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 12)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok for http://foo/bar: bad status returned')


if __name__ == '__main__':
    unittest.main()
