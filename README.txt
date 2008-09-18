superlance plugins for supervisor
=================================

Superlance is a package of plugin utilities for monitoring and
controlling processes that run under `supervisor
<http://supervisord.org>`_.

Currently, it provides only one script named ``httpok``.  This script
can be used as a supervisor event listener (subscribed to TICK events)
which will restart a "hung" HTTP server process, which is defined as a
process in the RUNNING state which does not respond in an appropriate
or timely manner to an HTTP GET request.


