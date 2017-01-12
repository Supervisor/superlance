import unittest
import superlance.httpctrl
from mock import Mock, call, patch
from supervisor.process import ProcessStates
from superlance.tests.dummy import (DummyRPCServer,
                                    DummySupervisorRPCNamespace,
                                    DummyResponse)
from superlance.httpctrl import HTTPCtrl

class HTTPCtrlTests(unittest.TestCase):
    def test_listProcesses_no_programs(self):
        programs = []
        ctrl = HTTPCtrl(DummyRPCServer(), programs, None, None)
        specs = list(ctrl.listProcesses())
        self.assertEqual(len(specs), 0)

    def test_listProcesses_w_RUNNING_programs_default_state(self):
        programs = ['foo']
        ctrl = HTTPCtrl(DummyRPCServer(), programs, None, None)
        specs = list(ctrl.listProcesses())
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0],
                         DummySupervisorRPCNamespace.all_process_info[0])

    def test_listProcesses_w_nonRUNNING_programs_default_state(self):
        programs = ['bar']
        ctrl = HTTPCtrl(DummyRPCServer(), programs, None, None)
        specs = list(ctrl.listProcesses())
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0],
                         DummySupervisorRPCNamespace.all_process_info[1])

    def test_listProcesses_w_RUNNING_programs_RUNNING_state(self):
        programs = ['foo', 'baz_01']
        ctrl = HTTPCtrl(DummyRPCServer(), programs, None, None)
        specs = list(ctrl.listProcesses(ProcessStates.RUNNING))
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0],
                         DummySupervisorRPCNamespace.all_process_info[0])

    def test_listProcesses_w_RUNNING_programs_STOPPED_state(self):
        programs = ['baz_01', 'foo']
        ctrl = HTTPCtrl(DummyRPCServer(), programs, None, None)
        specs = list(ctrl.listProcesses(ProcessStates.STOPPED))
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0],
                         DummySupervisorRPCNamespace.all_process_info[2])

    def test_listProcesses_w_RUNNING_groups_STOPPED_state(self):
        programs = ['baz']
        ctrl = HTTPCtrl(DummyRPCServer(), programs, None, None)
        specs = list(ctrl.listProcesses(ProcessStates.STOPPED))
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0],
                         DummySupervisorRPCNamespace.all_process_info[2])

    def test_parse_url(self):
        url = "http://foo:8080/bar?baz"
        ctrl = HTTPCtrl(DummyRPCServer(), [], url, None)
        (ConnClass, hostport, path) = ctrl.parse_url()

        self.assertEqual(ConnClass,
                         superlance.httpctrl.timeoutconn.TimeoutHTTPConnection,
                         msg = "Class not TimeoutHTTPConnection")
        self.assertEqual(hostport, "foo:8080", msg = "HTTP host incorrect")
        self.assertEqual(path, "/bar?baz", msg = "HTTP path incorrect")

        url = "https://foo:8080/"
        ctrl = HTTPCtrl(DummyRPCServer(), [], url, None)
        (ConnClass, hostport, path) = ctrl.parse_url()

        self.assertEqual(ConnClass,
                         superlance.httpctrl.timeoutconn.TimeoutHTTPSConnection,
                         msg = "Class not TimeoutHTTPSConnection")

    def test_runforever_notatick_atick(self):
        # Preparing mocks
        url = "http://foo/bar/baz"
        ctrl = HTTPCtrl(DummyRPCServer(), [], url, None)
        ctrl.parse_url = Mock(
            return_value = (Mock(side_effect=Exception("dummy exception")), None, None)
        )

        config = {'wait.side_effect': [
            ({'eventname': 'NOTATICK', 'len': 0}, None),
            ({'eventname': 'TICK', 'len': 0}, None)
        ]}
        childutils_listener_patch = patch("superlance.httpctrl.childutils.listener",
                                          **config)
        mock_wait = childutils_listener_patch.start()

        # Testing
        self.assertRaisesRegexp(Exception, "dummy exception", ctrl.runforever)
        self.assertEqual(mock_wait.mock_calls, [call.wait(), call.wait()])
        ctrl.parse_url.assert_called_with()

        childutils_listener_patch.stop()

    def test_runforever_inbody(self):
        # Preparing mocks
        url = "http://foo/bar?baz"
        ctrl = HTTPCtrl(DummyRPCServer(), ["baz_01"], url, "OK")

        config = {'wait.side_effect': [({'eventname': 'TICK', 'len': 0}, None)],
                  'ok.side_effect': [Exception("dummy exception")]
                 }
        childutils_listener_patch = patch("superlance.httpctrl.childutils.listener",
                                          **config)
        mock_wait = childutils_listener_patch.start()

        conn_mock = Mock()
        conn_class_mock = Mock(return_value = conn_mock)
        conn_mock.getresponse = Mock(return_value = DummyResponse())
        ctrl.parse_url = Mock(
            return_value = (conn_class_mock, "foo", "/bar")
        )

        ctrl.act = Mock()

        # Testing
        self.assertRaisesRegexp(Exception, "dummy exception", ctrl.runforever)
        self.assertEqual(mock_wait.mock_calls, [call.wait(), call.ok()])
        conn_mock.request.assert_called_once_with('GET', '/bar')
        ctrl.act.assert_called_once_with(start=True)

        childutils_listener_patch.stop()

    def test_act_start(self):
        # Preparing mocks
        ctrl = HTTPCtrl(DummyRPCServer(), ["baz", "maz"], None, None)
        ctrl.start_stop = Mock()
        ctrl.write_stderr = Mock()

        # Testing
        ctrl.act(start = True)
        ctrl.start_stop.assert_called_once_with(
            DummySupervisorRPCNamespace.all_process_info[2], True
        )
        ctrl.write_stderr.assert_called_with(
            "Programs states not changed because they did not exist: ['maz']"
        )

    def test_act_stop(self):
        # Preparing mocks
        ctrl = HTTPCtrl(DummyRPCServer(), ["foo", "maz"], None, None)
        ctrl.start_stop = Mock()
        ctrl.write_stderr = Mock()

        # Testing
        ctrl.act(start = False)
        ctrl.start_stop.assert_called_once_with(
            DummySupervisorRPCNamespace.all_process_info[0], False
        )
        ctrl.write_stderr.assert_called_with(
            "Programs states not changed because they did not exist: ['maz']"
        )

    def test_start_stop_stop(self):
        # Preparing mocks
        ctrl = HTTPCtrl(DummyRPCServer(), ["foo"], None, None)
        ctrl.rpc.supervisor.stopProcess = Mock()
        ctrl.write_stderr = Mock()

        # Testing
        ctrl.start_stop(DummySupervisorRPCNamespace.all_process_info[0],
                        start = False)
        ctrl.rpc.supervisor.stopProcess.assert_called_once_with("foo")

    def test_start_stop_start(self):
        # Preparing mocks
        ctrl = HTTPCtrl(DummyRPCServer(), ["baz_01"], None, None)
        ctrl.rpc.supervisor.startProcess = Mock()
        ctrl.write_stderr = Mock()

        # Testing
        ctrl.start_stop(DummySupervisorRPCNamespace.all_process_info[2],
                        start = True)
        ctrl.rpc.supervisor.startProcess.assert_called_once_with("baz:baz_01")

if __name__ == '__main__':
    unittest.main()
