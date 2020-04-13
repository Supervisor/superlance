superlance README
=================

Superlance is a package of plugin utilities for monitoring and controlling
processes that run under `supervisor <http://supervisord.org>`_.

Please see ``docs/index.rst`` for complete documentation.


增加对阿里巴巴-钉钉报警支持


[eventlistener:dingtalk_monitor]

command=crashdingtalk -p diting-monitor -p process  -dingtalk_secret "DingTalk secret" -dingtalk_hook_url "dingtalk hook url"
events=PROCESS_STATE_EXITED

redirect_stderr=false

buffer_size=100

