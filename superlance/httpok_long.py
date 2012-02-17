#!/usr/bin/env python
import httplib, socket
import sys, time
import optparse
import smtplib
from email.mime.text import MIMEText

SUBJECT_TEMPLATE ="{program} {host}:{port} seems down!"

MAIL_TEMPLATE = """{program} on host {host}:{port} seems down.
It returned {status} {reason} from uri {uri}.
Please Fix this!
"""

ERROR_MAIL_TEMPLATE = """{program} on host {host}:{port} seems down.
The following Exception occurred when running a HTTP-GET against: {uri}:

{exception}

Please fix this!
"""


def _write_stdout(s):
    sys.stdout.write(s)
    sys.stdout.flush()

def _write_stderr(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def send_mail(subject, body, _from, recipients, smtp_host="127.0.0.1", smtp_port=25):
    mime_text = MIMEText(body)
    mime_text["Subject"] = str(subject)
    mime_text["To"] = ", ".join(recipients)
    mime_text["From"] = _from
    _write_stderr(mime_text.as_string())
    smtp = smtplib.SMTP(smtp_host, smtp_port)
    smtp.sendmail(_from, recipients, mime_text.as_string())
    smtp.quit()

def http_ok():
    """
	supervisor-eventlistener for doing http-ok requests

	example-configuration:

	[eventlistener:httpok]
	event=TICK_60
	command=bin/http_ok_evenlistener.py --program="pernod" --interval=300 --uri="http://localhost:50%(process_num)02d/pernod/_health" --status=200 --mail=mfelsche@vz.net
	process_name=%(program_name)s_%(process_num)02d
	numprocs=2
	autorestart=true
    stderr-logfile=/tmp/%(program_name)s_%(process_num)02d.log
    """
    option_parser = optparse.OptionParser(
                                          description="event-listener for supervisor to run a http_ok command at a configurable interval",
                                          )
    option_parser.add_option("--program", dest="program", help="the program to observe, a human-readable-name", default="Pernod", metavar="Pernod")
    option_parser.add_option("--uri", dest="uri", help="the uri to contact", default=None)
    option_parser.add_option("--status", dest="status", help="the HTTP-Status to expect from uri", default=200, type="int", metavar=200)
    option_parser.add_option("--mail", dest="mail", help="comma-separated list of mail-adresses to receive mail on error", default=None)

    option_parser.add_option("--interval", dest="interval", type="int", help="the interval at which to do a httpok-run", default=300, metavar=300)
    option_parser.add_option("--one-shot", dest="one_shot", action="store_true", help="just do one shot, suitable for use in cronjobs", default=False)

    option_parser.add_option("--smtp-host", dest="smtp_host", type="string", help="the STMP-host to connect to for sending mail", default="127.0.0.1", metavar="127.0.0.1")
    option_parser.add_option("--smtp-port", dest="smtp_port", type="int", help="the SMTP-port to use for sending mail", default=25, metavar=25)

    options, args = option_parser.parse_args(sys.argv)

    if options.uri is None:
        _write_stderr("ERROR, please give a uri to ask for a HTTP-Response")
        return
    if options.mail is None:
        _write_stderr("ERROR, please give a emailadress to send error-notifications")
        return


    last_run = time.time()

    # extract host, port and path from uri
    rest = options.uri.split("://")[-1]
    try:
        host, port = rest.split(":")
        port, path = port.split("/", 1)
    except ValueError, msg:
        _write_stderr(str(msg))
        return

    port = port.split("?", 1)[0]


    long_running = True

    while long_running:
        _write_stdout('READY\n') # transition from ACKNOWLEDGED to READY
        line = sys.stdin.readline()  # read header line from stdin
        headers = dict([ x.split(':') for x in line.split() ])

        payload = sys.stdin.read(int(headers['len'])) # read the event payload
        _, timestamp = payload.split(":")
        try:
            timestamp = int(timestamp)
        except:
            _write_stderr("ERROR parsing payload: {0}",format(payload))
        else:
            now = time.time()
            if (now - last_run) > options.interval or options.one_shot:
                # set timestamp for the next round
                last_run = now
                try:
                    conn = httplib.HTTPConnection(host, int(port), timeout=2)
                    conn.request("GET", "/{path}".format(path=path) )
                    response = conn.getresponse()
                except Exception as e:
                    _write_stderr(str(e))
                    try:
                        send_mail(
                            SUBJECT_TEMPLATE.format(program=options.program, host=socket.getfqdn(), port=str(port)),
                            ERROR_MAIL_TEMPLATE.format(
                                program = options.program,
                                host = socket.getfqdn(),
                                port = port,
                                exception = str(e),
                                uri = options.uri,
                            ),
                            "root@{host}".format(host = socket.getfqdn()),
                            options.mail.split(","),
                            smtp_host = options.smtp_host,
                            smtp_port = options.smtp_port
                        )
                    except Exception as e:
                        _write_stderr(str(e))
                else:
                    if response.status != options.status:
                        try:
                            send_mail(
                                SUBJECT_TEMPLATE.format(program=options.program, host=socket.getfqdn(), port=str(port)),
                                MAIL_TEMPLATE.format(
                                    program = options.program,
                                    host = socket.getfqdn(),
                                    port = port,
                                    status = response.status,
                                    reason = response.reason,
                                    uri = options.uri,
                                ),
                                "root@{host}".format(host = socket.getfqdn()),
                                options.mail.split(","),
                                smtp_host = options.smtp_host,
                                smtp_port = options.smtp_port
                            )
                        except Exception as e:
                            _write_stderr(str(e))
        finally:
            _write_stdout('RESULT 2\nOK') # transition from READY to ACKNOWLEDGED
            long_running = not options.one_shot # stop if we are configured for a one-shot-run
