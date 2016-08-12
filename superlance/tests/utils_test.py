import unittest
import mock
import subprocess

from StringIO import StringIO

from superlance.compat import xmlrpclib
from superlance.utils import ExternalService, Log
from superlance.tests.dummy import (DummyRPCServer,
    DummySupervisorRPCNamespace)


class TestExternalService(unittest.TestCase):
    """
    Test class to test ExternalService class
    """
    @mock.patch('os.path.isfile')
    @mock.patch('sys.stderr', new_callable=StringIO)
    def setUp(self, mock_stderr, mock_os_path):
        """
        Setup function to initialise tests
        """
        self.stderr = mock_stderr
        mock_service_script = mock.MagicMock()
        self.ext_service = ExternalService(mock_service_script)

    def test_init(self):
        """
        Tests if ExternalService could be created
        """
        self.assertTrue(isinstance(self.ext_service, ExternalService))

    @mock.patch('os.path.isfile', side_effect=OSError)
    @mock.patch('sys.stderr', new_callable=StringIO)
    def test_init_fail(self, mock_stderr, mock_os_path):
        """
        Raise an exception when the service script does not exist
        """
        self.assertRaises(OSError, ExternalService, 'some script')

    @mock.patch('subprocess.check_call')
    def test_start_process(self, mock_sub):
        """
        Tests startProcess method
        """
        self.ext_service.startProcess('process')
        self.assertEqual('process started successfully\n',
                         self.stderr.getvalue())

    @mock.patch('subprocess.check_call',
                side_effect=subprocess.CalledProcessError('1', 'cmd'))
    def test_start_process_fail(self, mock_sub):
        """
        Tests startProcess method failure
        """
        self.ext_service.startProcess('process')
        self.assertEqual('process was unable to start. Cmd used to start: cmd',
                         self.stderr.getvalue())

    @mock.patch('subprocess.check_call')
    def test_stop_process(self, mock_sub):
        """
        Tests stopProcess method
        """
        self.ext_service.stopProcess('process')
        self.assertEqual('process stopped successfully\n',
                         self.stderr.getvalue())

    @mock.patch('subprocess.check_call',
                side_effect=subprocess.CalledProcessError('1', 'cmd'))
    def test_stop_process_fail(self, mock_sub):
        """
        Tests stopProcess method failure
        """
        self.ext_service.stopProcess('process')
        self.assertEqual('process was unable to stop. Cmd used to stop: cmd',
                         self.stderr.getvalue())


class TestLog(unittest.TestCase):
    """
    Test class to test Log class
    """
    @mock.patch('os.path.isfile')
    @mock.patch('sys.stderr', new_callable=StringIO)
    def setUp(self, mock_stderr, mock_os_path):
        """
        Setup function to initialise tests
        """
        self.stderr = mock_stderr
        self.log = Log(__name__)

    def test_log(self):
        """
        Tests basic logging
        """
        self.log.logger.error('Something happened')
        self.assertTrue('ERROR - utils_test - Something happened' in
            self.stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
