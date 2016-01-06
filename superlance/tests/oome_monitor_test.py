import unittest
import mock

from StringIO import StringIO

from superlance.compat import xmlrpclib
from superlance.oome_monitor import OomeMonitor, OomeProcess
from superlance.tests.dummy import (DummyRPCServer,
    DummySupervisorRPCNamespace)

class TestOomeProcess(unittest.TestCase):
    """
    Test class to test OomeProcess methods and properties
    """
    @mock.patch('sys.stderr', new_callable=StringIO)
    def setUp(self, mock_stderr):
        """
        Setup function to initialise tests
        """
        self.stderr = mock_stderr
        process_object = DummySupervisorRPCNamespace.all_process_info[0]
        self.process = OomeProcess(process_object, oome_file='oome_file')
    
    def test_init(self):
        """
        Tests if OomeProcess could be created
        """
        self.assertTrue(isinstance(self.process, OomeProcess))
        
    def test_env_vars(self):
        """
        Tests getting the env_vars property. Dummy env var resembles real
        environ file inside /proc/<pid>/
        """
        dummy_env_var = ("SUPERVISOR_GROUP_NAME=test_server\x00SUPERVISOR_PROC"
            "ESS_NAME=test_server\x00HOMEDIR=homedir\x00SUPERVISOR_ENABLED=1"
            "\x00SUPERVISOR_SERVER_URL=unix:///tmp/supervisor.sock\x00OOME_FIL"
            "E=oome_file")
        expected = {'OOME_FILE': 'oome_file', 'HOMEDIR': 'homedir'}
        with mock.patch('superlance.oome_monitor.open',
                mock.mock_open(read_data=dummy_env_var), create=True) as m:
            self.assertEqual(sorted(expected.items()),
                             sorted(self.process.env_vars.items()))
    
    def test_get_oome_file_oome_file_init(self):
        """
        Tests getting the oome_file name property if it was set during init
        """
        self.assertEqual('oome_file', self.process.oome_file)
    
    def test_get_oome_file_oome_file_env(self):
        """
        Tests getting the oome_file name property if $OOME_FILE is in env vars
        """
        self.process._oome_file = None
        self.process._env_vars = {'OOME_FILE': 'oome_file_environ'}
        self.assertEqual('oome_file_environ', self.process.oome_file)
    
    def test_get_oome_file_homedir_env(self):
        """
        Tests getting the oome_file name property if $HOMEDIR is in env vars
        """
        self.process._oome_file = None
        self.process._env_vars = {'HOMEDIR': 'homedir'}
        self.assertEqual('homedir/state/foo.oome', self.process.oome_file)
    
    @mock.patch('superlance.oome_monitor.psutil')
    def test_get_oome_file_cwd(self, mock_psutil):
        """
        Tests getting the oome_file name property if no env variables were set
        """
        mock_psutil.Process.return_value.cwd.return_value = 'cwd'
        self.process._oome_file = None
        self.process._env_vars = {'USELESS_VAR': '3.141599'}
        self.assertEqual('cwd/state/foo.oome', self.process.oome_file)
        
    def test_set_oome_file(self):
        """
        Tests setting oome_file property
        """
        self.process.oome_file = 'real_oome_file'
        self.assertEqual('real_oome_file', self.process.oome_file)
    

    @mock.patch('superlance.oome_monitor.os.path.isfile',
                return_value=True)
    def test_check_oome_file_exists(self, mock_os_path):
        """
        Tests checking oome_file existence
        """
        self.assertTrue(self.process.check_oome_file())
    
    @mock.patch('superlance.oome_monitor.os.path.isfile',
                return_value=False)
    def test_check_oome_file_does_not_exist(self, mock_os_path):
        """
        Tests checking oome_file non existence
        """
        self.assertFalse(self.process.check_oome_file())
    
    @mock.patch('superlance.oome_monitor.os.remove', return_value=True)
    def test_oome_file_delete(self, mock_os_remove):
        """
        Tests deleting the oome file
        """
        self.process.delete_oome_file()
        self.assertEqual("oome file oome_file was deleted\n",
                         self.stderr.getvalue())
    
    @mock.patch('superlance.oome_monitor.os.remove',
                side_effect=OSError('file'))
    def test_oome_file_delete(self, mock_os_remove):
        """
        Tests deleting the oome file failure
        """
        self.process.delete_oome_file()
        self.assertEqual("oome file could not be removed: file\n",
                         self.stderr.getvalue())
    

class TestOomeMonitor(unittest.TestCase):
    """
    Test class to test OomeMonitor methods and properties
    """
    @mock.patch('sys.stdin', new_callable=StringIO)
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('sys.stderr', new_callable=StringIO)
    def setUp(self, mock_stderr, mock_stdout, mock_stdin):
        """
        Setup function to initialise tests
        """
        rpc = DummyRPCServer()
        process_name = ['foo']
        self.stderr = mock_stderr
        self.stdout = mock_stdout
        self.stdin = mock_stdin
        self.oome_monitor_all = OomeMonitor(rpc, all=True)
        self.oome_monitor_single = OomeMonitor(rpc, process_name=process_name)
        dummy_supervisor = DummySupervisorRPCNamespace()
        self.oome_monitor_all.rpc.supervisor = dummy_supervisor
        
    def test_init(self):
        """
        Tests OomeMonitor object creation
        """
        self.assertTrue(isinstance(self.oome_monitor_all, OomeMonitor))
        self.assertTrue(isinstance(self.oome_monitor_single, OomeMonitor))
        
    def test_generate_processes(self):
        """
        Tests OomeMonitor _generate_processes method
        """
        self.assertEqual(len(self.oome_monitor_all.processes),
            len(DummySupervisorRPCNamespace.all_process_info))
        self.assertEqual(len(self.oome_monitor_single.processes), 1)
    
    def test_write_stderr(self):
        """
        Tests write_stderr
        """
        self.oome_monitor_all.write_stderr('some message')
        self.assertEqual('some message\n',
            self.stderr.getvalue())

    def test_procs(self):
        """
        Tests OomeMonitor.procs property
        """
        self.assertEqual(self.oome_monitor_all.procs,
            DummySupervisorRPCNamespace.all_process_info)
        # It should match to "foo" process defined in Dummy
        self.assertEqual(self.oome_monitor_single.procs,
            DummySupervisorRPCNamespace.all_process_info[:1])

    def test_restart(self):
        """
        Tests OomeMonitor.restart method
        """
        self.oome_monitor_all.restart(
            DummySupervisorRPCNamespace.all_process_info[0])
        self.oome_monitor_single.restart(
            DummySupervisorRPCNamespace.all_process_info[0])
        self.assertEqual('foo restarted\nfoo restarted\n',
            self.stderr.getvalue())
        
    def test_failed_restart(self):
        """
        Tests OomeMonitor.restart method failure
        """
        self.oome_monitor_all.rpc.supervisor.stopProcess = mock.MagicMock(
            side_effect=xmlrpclib.Fault('stop', 'error'))
        self.oome_monitor_all.rpc.supervisor.startProcess = mock.MagicMock(
            side_effect=xmlrpclib.Fault('start', 'error'))
        self.oome_monitor_all.restart(
            DummySupervisorRPCNamespace.all_process_info[0])
        self.assertEqual("Failed to stop process foo: <Fault stop: 'error'>\n"
            "Failed to start process foo: <Fault start: 'error'>\n",
            self.stderr.getvalue())
    
    @mock.patch('superlance.oome_monitor.psutil')
    def test_run(self, mock_psutil):
        """
        Functional test for run() all method with one of the processes (bar) having
        an oome file. OomeMonitor will try to delete the mocked oome file
        and restart the process (using dummy rpc.supervisor)
        """
        self.stdin.write('eventname:TICK len:0\n')
        self.stdin.seek(0)
        # returning that the process has an oome file
        self.oome_monitor_all.processes[1].check_oome_file = mock.MagicMock()
        # mocking the actual file delete
        self.oome_monitor_all.processes[1].delete_oome_file = mock.MagicMock()
        with mock.patch('superlance.oome_monitor.open',
                        mock.mock_open(read_data='test'), create=True) as m:
            self.oome_monitor_all.run(test=True)
        self.assertEqual("bar restarted\n", self.stderr.getvalue())
    
    @mock.patch('superlance.oome_monitor.psutil')
    def test_run_sigle(self, mock_psutil):
        """
        Functional test for run() single method with the processes (foo) having
        an oome file. OomeMonitor will try to delete the mocked oome file
        and restart the process (using dummy rpc.supervisor)
        """
        self.stdin.write('eventname:TICK len:0\n')
        self.stdin.seek(0)
        # returning that the process has an oome file
        self.oome_monitor_single.processes[0].check_oome_file = \
            mock.MagicMock()
        # mocking the actual file delete
        self.oome_monitor_single.processes[0].delete_oome_file = \
            mock.MagicMock()
        with mock.patch('superlance.oome_monitor.open',
                        mock.mock_open(read_data='test'), create=True) as m:
            self.oome_monitor_single.run(test=True)
        self.assertEqual("foo restarted\n", self.stderr.getvalue())
        
    @mock.patch('superlance.oome_monitor.psutil')
    def test_dry_run(self, mock_psutil):
        """
        Functional test for run() method with one of the processes (bar) having
        an oome file. OomeMonitor will not try to delete the mocked oome file
        or restart the process due to dry run
        """
        self.stdin.write('eventname:TICK len:0\n')
        self.stdin.seek(0)
        self.oome_monitor_all.dry = True
        # returning that the process has an oome file
        self.oome_monitor_all.processes[1].check_oome_file = mock.MagicMock()
        # mocking the actual file delete
        self.oome_monitor_all.processes[1].delete_oome_file = mock.MagicMock()
        with mock.patch('superlance.oome_monitor.open',
                        mock.mock_open(read_data='test'), create=True) as m:
            self.oome_monitor_all.run(test=True)
        self.assertEqual("oome file is detected for bar, not restarting due to"
                         " dry-run\n", self.stderr.getvalue())
        
if __name__ == '__main__':
    unittest.main()