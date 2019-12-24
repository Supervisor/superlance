# -*- coding:utf-8

"""
Author: xiaolong.pang <pangxiaolong@lanyife.com>
Date: 2019/12/23
"""
import argparse
import sys
import urllib2
import urllib
import json
import time, hmac, hashlib, base64
import socket

doc  = """
    Hello world
"""


def gen_dingtalk_secret(args):
    timestamp = long(round(time.time() * 1000))
    secret_enc = bytes(args.dingtalk_secret).encode("utf-8")
    raw_data = "{}\n{}".format(timestamp, secret_enc)
    raw_data_enc = bytes(raw_data).encode("utf-8")

    hash_hac = hmac.new(secret_enc, raw_data_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.quote_plus(base64.b64encode(hash_hac))

    return timestamp, sign

def get_hostname():
    return socket.gethostbyname()

def notify(args, subject, msg):
    timestamp, sign = gen_dingtalk_secret(args)
    j = {
        "msgtype": "markdown",
        "markdown": {
            "title": "supervisord 告警: %s",
            "text": """
                ### Supervisor 告警 \n
                ### hostname {hostname}
            """.format(hostname=self.)
        }.,
        "isAtAll": True,
    }

    r = urllib2.Request(args.dingtalk_hook_url + "&timestamp=%s&sign=%s" % (timestamp, sign), headers={
        "Content-Type": "application/json"
    })

    print(args.dingtalk_hook_url + "&timestmap=%s&sign=%s" % (timestamp, sign))
    fp = urllib2.urlopen(r, data=json.dumps(j))
    r = fp.read()
    fp.close()

    print(r)


def main(argv=sys.argv):
    command_parser = argparse.ArgumentParser()
    command_parser.add_argument("-p", dest="programs", required=True, type=str, help=doc, action="append")
    command_parser.add_argument("-dingtalk_hook_url", dest="dingtalk_hook_url", type=str, required=True, help=doc)
    command_parser.add_argument("-dingtalk_secret", dest="dingtalk_secret", type=str, required=True, help=doc)
    command_parser.add_argument("-a", dest="any", type=bool, required=False, help=doc)
    args = command_parser.parse_args()

    notify(args, "测试", "测试发出")



main()