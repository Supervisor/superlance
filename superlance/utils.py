#!/usr/bin/env python
#
# Module contains common utility classes used throughout the superlance
#

import logging
import os.path
import subprocess
import sys

from supervisor.rpcinterface import SupervisorNamespaceRPCInterface

class ExternalService(object):
    """ This class provides start and stop functions which call external scripts
    and are intended to be compatible with the same RPC functions in
    SupervisorNamespaceRPCInterface class.

    In order to use this, consumers need to instantiate this and call the
    functions of this class instead of ones in RPC interface to supervisord.

    External service script needs to accept "start" and "stop" arguments and
    obviously perform the same.
    """
    def __init__(self, external_service):
        """ Initialise and setup an external service script

        @param string external_service External service script path
        """
        if os.path.isfile(external_service):
            self.service = external_service
        else:
            raise OSError(2,
                'service script does not exist or permission was denied',
                external_service)
        self.stderr = sys.stderr


    def startProcess(self, name, wait=True):
        """ Start a process

        @param string name Process name (or ``group:name``, or ``group:*``)
        @param boolean wait Wait for process to be fully started
        @return boolean result     Always true unless error

        """
        try:
            subprocess.check_call([self.service, 'start'], stdout=self.stderr)
            self.stderr.write('{0} started successfully\n'.format(name))
        except subprocess.CalledProcessError as e:
            self.stderr.write('{0} was unable to start. Cmd used to start: {1}'
                .format(name, e.cmd))
        self.stderr.flush()
        return True

    def stopProcess(self, name, wait=True):
        """ Stop a process named by name

        @param string name  The name of the process to stop (or 'group:name')
        @param boolean wait        Wait for the process to be fully stopped
        @return boolean result     Always return True unless error
        """
        try:
            subprocess.check_call([self.service, 'stop'], stdout=self.stderr)
            self.stderr.write('{0} stopped successfully\n'.format(name))
        except subprocess.CalledProcessError as e:
            self.stderr.write('{0} was unable to stop. Cmd used to stop: {1}'
                .format(name, e.cmd))
        self.stderr.flush()
        return True


class Log(object):
    """
    Utility class which handles logging for superlance modules
    """
    def __init__(self, name):
        formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - '
            '%(module)s - %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)
