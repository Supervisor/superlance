import socket
import time
import unittest
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
                if exc is True:
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

    def _makeOne(self, *args, **kwargs):
        return self._getTargetClass()(*args, **kwargs)

    def _makeOnePopulated(self, programs, any=None, statuses=None, inbody=None,
                          eager=True, gcore=None, coredir=None,
                          response=None, exc=None, name=None):
        if statuses is None:
            statuses = [200]
        if response is None:
            response = DummyResponse()
        httpok = self._makeOne(
            programs=programs,
            any=any,
            statuses=statuses,
            inbody=inbody,
            eager=eager,
            coredir=coredir,
            gcore=gcore,
            name=name,
            rpc=DummyRPCServer(),
            url='http://foo/bar',
            timeout=10,
            email='chrism@plope.com',
            sendmail='cat - > /dev/null',
            retry_time=0,
            )
        httpok.stdin = StringIO()
        httpok.stdout = StringIO()
        httpok.stderr = StringIO()
        httpok.connclass = make_connection(response, exc=exc)
        return httpok

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
        any = None
        prog = self._makeOnePopulated(programs, any)
        prog.stdin.write('eventname:NOTATICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        self.assertEqual(prog.stderr.getvalue(), '')

    def test_runforever_doesnt_act_if_status_is_expected(self):
        statuses = [200, 201]
        for status in statuses:
            response = DummyResponse()
            response.status = status # expected
            prog = self._makeOnePopulated(
                programs=['foo'],
                statuses=statuses,
                response=response,
                )
            prog.stdin.write('eventname:TICK len:0\n')
            prog.stdin.seek(0)
            prog.runforever(test=True)
            # status is expected so there should be no output
            self.assertEqual('', prog.stderr.getvalue())

    def test_runforever_acts_if_status_is_unexpected(self):
        statuses = [200, 201]
        response = DummyResponse()
        response.status = 500 # unexpected
        response.reason = 'Internal Server Error'
        prog = self._makeOnePopulated(
            programs=['foo'],
            statuses=[statuses],
            response=response,
            )
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertTrue('Subject: httpok: http://foo/bar: '
                        'bad status returned' in lines)
        self.assertTrue('status contacting http://foo/bar: '
                        '500 Internal Server Error' in lines)

    def test_runforever_doesnt_act_if_inbody_is_present(self):
        response = DummyResponse()
        response.body = 'It works'
        prog = self._makeOnePopulated(
            programs=['foo'],
            statuses=[response.status],
            response=response,
            inbody='works',
            )
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        # body is expected so there should be no output
        self.assertEqual('', prog.stderr.getvalue())

    def test_runforever_acts_if_inbody_isnt_present(self):
        response = DummyResponse()
        response.body = 'Some kind of error'
        prog = self._makeOnePopulated(
            programs=['foo'],
            statuses=[response.status],
            response=response,
            inbody="works",
            )
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertTrue('Subject: httpok: http://foo/bar: '
                        'bad body returned' in lines)

    def test_runforever_eager_error_on_request_some(self):
        programs = ['foo', 'bar', 'baz_01', 'notexisting']
        any = None
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
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
                    'Subject: httpok: http://foo/bar: bad status returned')

    def test_runforever_eager_error_on_request_any(self):
        programs = []
        any = True
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
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
                    'Subject: httpok: http://foo/bar: bad status returned')

    def test_runforever_eager_error_on_process_stop(self):
        programs = ['FAILED']
        any = False
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.rpc.supervisor.all_process_info = _FAIL
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
        self.assertEqual(lines[0], "Restarting selected processes ['FAILED']")
        self.assertEqual(lines[1], 'foo:FAILED is in RUNNING state, restarting')
        self.assertEqual(lines[2],
                    "Failed to stop process foo:FAILED: <Fault 30: 'FAILED'>")
        self.assertEqual(lines[3], 'foo:FAILED restarted')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 10)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok: http://foo/bar: bad status returned')

    def test_runforever_eager_error_on_process_start(self):
        programs = ['SPAWN_ERROR']
        any = False
        prog = self._makeOnePopulated(programs, any, exc=True)
        prog.rpc.supervisor.all_process_info = _FAIL
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        lines = prog.stderr.getvalue().split('\n')
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
                    'Subject: httpok: http://foo/bar: bad status returned')

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
                    'Subject: httpok: http://foo/bar: bad status returned')

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
        self.assertEqual(lines[1], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[2], 'foo restarted')
        self.assertEqual(lines[3], 'bar not in RUNNING state, NOT restarting')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 10)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok: http://foo/bar: bad status returned')

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
        self.assertEqual(lines[1], 'foo is in RUNNING state, restarting')
        self.assertEqual(lines[2], 'foo restarted')
        self.assertEqual(lines[3], 'bar not in RUNNING state, NOT restarting')
        mailed = prog.mailed.split('\n')
        self.assertEqual(len(mailed), 10)
        self.assertEqual(mailed[0], 'To: chrism@plope.com')
        self.assertEqual(mailed[1],
                    'Subject: httpok: http://foo/bar: bad status returned')

    def test_subject_no_name(self):
        """set the name to None to check if subject formats to:
        httpok: %(subject)s
        """
        prog = self._makeOnePopulated(
            programs=['foo', 'bar'],
            any=None,
            eager=False,
            exc=[ValueError('this causes status to be None')],
            name=None,
            )
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        mailed = prog.mailed.split('\n')
        self.assertEqual(mailed[1],
          'Subject: httpok: http://foo/bar: bad status returned')

    def test_subject_with_name(self):
        """set the name to a string to check if subject formats to:
        httpok [%(name)s]: %(subject)s
        """
        prog = self._makeOnePopulated(
            programs=['foo', 'bar'],
            any=None,
            eager=False,
            exc=[ValueError('this causes status to be None')],
            name='thinko',
            )
        prog.stdin.write('eventname:TICK len:0\n')
        prog.stdin.seek(0)
        prog.runforever(test=True)
        mailed = prog.mailed.split('\n')
        self.assertEqual(mailed[1],
          'Subject: httpok [thinko]: http://foo/bar: bad status returned')

if __name__ == '__main__':
    unittest.main()
