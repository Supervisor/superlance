import datetime
import os
import sys
import time

from supervisor import childutils

doc = '''
Usage: timemon -g taskgroup -i hour -n 5 [ -s 3 ]

Restarts daemon every 5 hours. Sleep between restarts - 3 seconds
'''


def write_stdout(s):
    # only eventlistener protocol messages may be sent to stdout
    sys.stdout.write(s)
    sys.stdout.flush()


def write_stderr(s):
    sys.stderr.write(s)
    sys.stderr.flush()


def timemon_from_args(arguments):
    import getopt
    short_args = "hg:i:n:s"
    long_args = [
        "help",
        "group=",
        "interval=",
        "number=",
        "sleep="
    ]

    if not arguments:
        return None
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        return None

    timemon_args = {}
    for option, value in opts:

        if option in ('-h', '--help'):
            return None

        if option in ('-g', '--group'):
            timemon_args['group'] = value

        if option in ('-i', '--interval'):
            timemon_args['interval'] = value

        if option in ('-n', '--number'):
            timemon_args['number'] = value

        if option in ('-s', '--sleep'):
            timemon_args['sleep'] = value
    return timemon_args


def usage():
    print(doc)
    sys.exit(255)


def start_timemon(group, interval, number, sleep=0):
    max_serial = 0
    while True:
        rpc = childutils.getRPCInterface(os.environ)
        hdrs, payload = childutils.listener.wait(sys.stdin, sys.stdout)
        if int(hdrs['serial']) <= max_serial:
            continue
        max_serial = int(hdrs['serial'])
        process_info = rpc.supervisor.getAllProcessInfo()
        should_restart = getattr(datetime.datetime.now(), interval) % int(number)
        if should_restart:
            for process in process_info:
                if process['group'] == group and \
                   should_restart:
                    try:
                        rpc.supervisor.stopProcess(':'.join([process['group'], process['name']]), True)
                    except Exception as e:
                        write_stderr(str(e) + "\n")
                    if sleep:
                        time.sleep(float(sleep))
                    try:
                        rpc.supervisor.startProcess(':'.join([process['group'], process['name']]), True)
                    except Exception as e:
                        write_stderr(str(e) + "\n")
        write_stdout("RESULT 2\nOK")


def main():
    timemon_args = timemon_from_args(sys.argv[1:])
    if timemon_args is None:
        usage()
    start_timemon(**timemon_args)
if __name__ == '__main__':
    main()
