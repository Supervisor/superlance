superlance plugins for supervisor
=================================

Superlance is a package of plugin utilities for monitoring and
controlling processes that run under `supervisor
<http://supervisord.org>`_.

Currently, it provides two scripts:

``httpok`` -- This script can be used as a supervisor event listener
(subscribed to TICK events) which will restart a "hung" HTTP server
process, which is defined as a process in the RUNNING state which does
not respond in an appropriate or timely manner to an HTTP GET request.

``crashmail`` -- This script will email a user when a process enters
the EXITED state unexpectedly.

``memmon`` -- See the description below.


Memmon Overview
---------------

memmon is a supervisor "event listener" which may be subscribed to a
concrete TICK_x event. When memmon receives a TICK_x event (TICK_60 is
recommended, indicating activity every 60 seconds), memmon checks that a
configurable list of programs (or all programs running under supervisor) are
not exceeding a configurable about of memory (resident segment size, or RSS).
If one or more of these processes is consuming more than the amount of memory
that memmon believes it should, memmon will restart the process. memmon can be
configured to send an email notification when it restarts a process.

memmon is known to work on Linux and Mac OS X, but has not been tested on
other operating systems (it relies on ps output and command-line switches).

memmon is incapable of monitoring the process status of processes which are
not supervisord child processes.

Memmon Command
--------------

memmon is a "console script" installed when you install supervisor. Although
memmon is an executable program, it isn't useful as a general-purpose script:
it must be run as a supervisor event listener to do anything useful. memmon
accepts the following options:

  Option       Argument(s)      Description
  -----------  ---------------  ----------------------
  -h           N/A              Show program help.
  --help

  -p           name/size pair   A name/size pair, e.g. "foo=1MB". The name 
  --program                     represents the supervisor program name that 
                                you'd like memmon to monitor, the size represents
                                the number of bytes (suffix-multiplied using "KB", 
                                "MB" or "GB") that should be considered "too much".
                                Multiple -p options can be provided to memmon to
                                signify that you'd like to monitor more than one 
                                program. Programs can be specified as a "namespec",
                                to disambiguate same-named programs in different
                                groups, e.g. "foo:bar" represents the program "bar"
                                in the "foo" group.

  -g           name/size pair   A groupname/size pair, e.g. "group=1MB". The name
  --groupname                   represents the supervisor group name that you'd
                                like memmon to monitor, the size represents the
                                number of bytes (suffix-multiplied using "KB", "MB"
                                or "GB") that should be considered "too much". 
                                Multiple -g options can be provided to memmon to
                                signify that you'd like to monitor more than one
                                group.  If any process in this group exceeds the 
                                maximum, it will be restarted.   

  -a           size             A size (suffix-multiplied using "KB", "MB" or "GB") 
  --any                         that should be considered "too much". If any program
                                running as a child of supervisor exceeds this maximum,
	 	                            it will be restarted. E.g. 100MB. 

  -s           command          A command that will send mail if passed the email 
  --sendmail                    body (including the headers).  Defaults to
    _program                    "/usr/sbin/sendmail -t -i". Specifying this doesn't 
                                cause memmon to send mail by itself (see the 
                                -m/--email option). 

  -m           email address    An email address to which to send email when a process
  --email                       is restarted. By default, memmon will not send any mail
                                unless an email address is specified. 

Configuring Memmon Into the Supervisor Config
---------------------------------------------

An [eventlistener:x] section must be placed in supervisord.conf in order for
memmon to begin working. See the "Events" chapter in the Supervisor manual
for more information about event listeners. The following examples assume that
the memmon is on your system PATH.

    memmon Example Configuration 1

        This configuration causes memmon to restart any process which is a
        child of supervisord consuming more than 200MB of RSS, and will send
        mail to bob@example.com when it restarts a process using the default
        sendmail command.

        [eventlistener:memmon]
        command=memmon -a 200MB -m bob@example.com
        events=TICK_60

    memmon Example Configuration 2

        This configuration causes memmon to restart any process with the
        supervisor program name "foo" consuming more than 200MB of RSS, and
        will send mail to bob@example.com when it restarts a process using the
        default sendmail command.

        [eventlistener:memmon]
        command=memmon -p foo=200MB -m bob@example.com
        events=TICK_60

    memmon Example Configuration 3            

        This configuration causes memmon to restart any process in the process
        group "bar" consuming more than 200MB of RSS, and will send mail to
        bob@example.com when it restarts a process using the default sendmail
        command.

        [eventlistener:memmon]
        command=memmon -g bar=200MB -m bob@example.com
        events=TICK_60
