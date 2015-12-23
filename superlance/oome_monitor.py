#!/usr/bin/env python
import argparse
import os
import os.path
import sys

import psutil

from superlance.compat import xmlrpclib
from supervisor import childutils
from supervisor.options import make_namespec

DESCRIPTION = """An event listener needs to be subscribed to TICK_60 (or TICK_5)
events, which restarts processes that are children of supervisord based on the
out-of-memory error conditions. The listener will monitor specified directory
for a "*.oome" file and restart the processes accordingly.

oome_monitor will try to guess *.oome absolute file path based on
the following:
  * If its provided as an argument - use that
  * $OOME_FILE environment variable of the process
  * $HOMEDIR environment variable and the process name + .oome
  * $CWD of the process and the process name + .oome
  
oome_monitor could be run to monitor all supervisord processes or specified
ones inside the configuration file. In case if only one process is monitored
it is possible to provide absolute path of the oome file, e.g. in case if
app is started in non standard way.

An example supervisor config snippets that tells supervisor to use oome_monitor
as a listener is below:

# To configure all supervisord daemons
[eventlistener:oome_listener]
command=oome_monitor all
events=TICK_60

# To configure specific applications to be monitored
[eventlistener:oome_listener]
command=oome_monitor single -p webapp1 -p webapp2
events=TICK_5

# To configure one app with specific oome file
[eventlistener:oome_listener]
command=oome_monitor single -p webapp -o /tmp/webapp.oome
events=TICK_60

# Dry run / test mode
[eventlistener:oome_listener]
command=oome_monitor all -d
events=TICK_5
"""

class OomeProcess(object):
    """
    Class to contain process related definitions related to OomeMonitor
    """
    def __init__(self, process_object, oome_file=None):
        """
        :param process_object: Process data structure returned by
            supervisor.rpc.getProcessInfo()
        :type process_object: dict
        :param oome_file: oome file name to check if specified,
            otherwise autodetect
        :type oome_file: str
        """
        self.process = process_object
        self.oome_file = oome_file
        self.stderr = sys.stderr
        self._env_vars = None
    
    @property
    def env_vars(self):
        """
        Cache and return environment variables for the process.
        
        :returns: Process environment variables dictionary
        :rtype: dict
        """
        if not self._env_vars:
            with open('/proc/{}/environ'.format(self.process['pid'])) as f:
                self._env_vars = dict(
                    x.split('=')
                    for x in f.read().split('\x00')
                    if x.startswith('OOME_FILE')
                    or x.startswith('HOMEDIR')
                )
        return self._env_vars
    
    @property
    def oome_file(self):
        """
        Returns the oome file name with absolute path.
        
        :returns: oome file name
        :rtype: str
        """
        # if self._oome_file is not defined try to guess
        if not self._oome_file:
            if 'OOME_FILE' in self.env_vars:
                # if the oome env var is set - use it
                self.oome_file = self.env_vars['OOME_FILE']
            else:
                # otherwise try to generate it
                if 'HOMEDIR' in self.env_vars:
                    # Use the HOMEDIR env var if its set
                    cwd = self.env_vars['HOMEDIR']
                else:
                    # Otherwise get the process cwd
                    process = psutil.Process(self.process['pid'])
                    cwd = process.cwd()
                self.oome_file = '{}/state/{}.oome'.format(cwd,
                        self.process['name'])
        return self._oome_file
    
    @oome_file.setter
    def oome_file(self, value):
        """
        Sets the oome file name with absolute path.
        
        :param value: absolute file name
        :type value: str
        """
        self._oome_file = value
        
    def check_oome_file(self):
        """
        Check if "oome" file for this process exists in the file system.

        :returns: Boolean result whether file exists or not
        :rtype: bool
        """
        if os.path.isfile(self.oome_file):
            return True
        else:
            return False
        
    def delete_oome_file(self):
        """
        Delete the oome file.
        """
        try:
            os.remove(self.oome_file)
            msg = 'oome file {} was deleted\n'.format(self.oome_file)
        except OSError as e:
            msg = 'oome file could not be removed: {}\n'.format(e)
        self.stderr.write(msg)
        self.stderr.flush()


class OomeMonitor(object):
    """
    Class for performing actions when 'oome' file is detected inside webapp
    state/ directory.
    """
    def __init__(self, rpc, process_name=[], all=False, dry=False,
                 oome_file=None):
        """
        We explicitly define self.stdin, self.stdout, and self.stderr
        so this code could be unit tested.
        
        :param rpc: RPC interface to connect to supervisord
        :type rpc: xmlrpclib.ServerProxy
        :param process_name: Process name(s) to monitor and restart
        :type process_name: list or tuple
        :param all: All process names to monitor
        :type all: bool
        :param dry: Specify the dry run value
        :type dry: bool
        :param oome_file: oome file name to check if specified,
            otherwise autodetect
        :type oome_file: str
        """
        self.all = all
        self.dry = dry
        self.oome_file = oome_file
        self.process_names = process_name
        self.rpc = rpc
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self._generate_processes()
        
    def _generate_processes(self):
        """
        Generate OomeProcess objects.
        """
        self.processes = []
        if len(self.process_names) > 1 or self.all:
            for process in self.procs:
                proc = OomeProcess(process)
                self.processes.append(proc)
        else:
            proc = OomeProcess(self.procs[0], oome_file=self.oome_file)
            self.processes.append(proc)
    
    def write_stderr(self, msg):
        """
        Send arbitrary messages to supervisord which will be logged into file.
        
        :param msg: Message to send
        :type msg: str
        """
        self.stderr.write('{}\n'.format(msg))
        self.stderr.flush()
    
    @property
    def procs(self):
        """
        Returns the list of processes to act on. We don't cache here in order
            to get up to date information on every call.
        
        :returns: List of processes
        :rtype: list
        """
        if self.all:
            return self.rpc.supervisor.getAllProcessInfo()
        else:
            return [x for x in self.rpc.supervisor.getAllProcessInfo()
                 if x['name'] in self.process_names]
        
    def restart(self, process):
        """
        Restart the given supervisord process (not the OomeProcess)
        
        :param process: Process data structure returned by
            supervisor.rpc.getProcessInfo()
        :type process: dict
        """
        namespec = make_namespec(process['group'], process['name'])
        try:
            self.rpc.supervisor.stopProcess(namespec)
        except xmlrpclib.Fault as e:
            self.write_stderr(
                'Failed to stop process {}: {}'.format(namespec, e))
        try:
            self.rpc.supervisor.startProcess(namespec)
        except xmlrpclib.Fault as e:
            self.write_stderr(
                'Failed to start process {}: {}'.format(namespec, e))
        else:
            self.write_stderr('{} restarted'.format(namespec))
        
    def run(self, test=False):
        """
        Main event loop function of the OomeMonitor
        """
        while 1:
            # read header and payload
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)
            if not headers['eventname'].startswith('TICK'):
                # do nothing with non-TICK events
                childutils.listener.ok(self.stdout)
                continue
            # For each process check for an oome file and restart it if True
            for oome_process in self.processes:
                if oome_process.check_oome_file():
                    if self.dry:
                        self.write_stderr(
                            'oome file is detected for {}, not restarting due '
                            'to dry-run'.format(oome_process.process['name']))
                    else:
                        # delete the oome file first
                        oome_process.delete_oome_file()
                        # restart the process
                        self.restart(oome_process.process)
    
            # transition from READY to ACKNOWLEDGED
            childutils.listener.ok(self.stdout)
            if test:
                break

def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    dry_run_text = ('do not actually kill or restart the procesesses, '
              'only log the actions.')
    subparsers = parser.add_subparsers(title='subcommands',
        description='choose one of the subcommands below',
        help='choose to monitor single supervisord process or all of them')
    parser_p = subparsers.add_parser('single')
    parser_p.add_argument('--process-name', '-p', action='append',
        required=True, help=('specify one or more supervisor process_names '
                             'to monitor.'))
    parser_p.add_argument('--oome-file', '-o',
        help='for single process optionally provide an oome file name')
    parser_p.add_argument('--dry', '-d', action='store_true',
        help=dry_run_text)
    parser_a = subparsers.add_parser('all')
    parser_a.add_argument('all', action='store_true',
        help='monitor all supervisor processes.')
    parser_a.add_argument('--dry', '-d', action='store_true',
        help=dry_run_text)
    args = parser.parse_args()
    try:
        if len(args.process_name) > 1 and args.oome_file:
            sys.stderr.write('you cannot specify oome file name when multiple '
                             'supervisord processes are to be monitored\n')
            sys.stderr.flush()
            return
    except AttributeError:
        # We don't care if "all" was selected
        pass
    try:
        rpc = childutils.getRPCInterface(os.environ)
    except KeyError as e:
        if e.args[0] != 'SUPERVISOR_SERVER_URL':
            raise
        sys.stderr.write('oome_monitor must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return
    monitor = OomeMonitor(rpc, **vars(args))
    monitor.run()

if __name__ == '__main__':
    main()