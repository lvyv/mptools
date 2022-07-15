#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : http_request.py
# @Time    : 2022/7/6 17:45
# @Author  : XiongFei
# Description：

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class HttpRequest:
    def __init__(self, connect_time_out=3, read_time_out=3):
        self._connect_time_out = connect_time_out
        self._read_time_out = read_time_out
        self._resp = None

    def _do_http_request(self, _type, _url, _data=None, _file=None):
        _headers = {'Content-Type': 'application/json'}
        try:
            if _type == 'GET':
                self._resp = requests.get(_url, verify=False, headers=_headers,
                                          timeout=(self._connect_time_out, self._read_time_out))
            else:
                self._resp = requests.post(_url, verify=False, data=_data, files=_file,
                                           timeout=(self._connect_time_out, self._read_time_out))
        except requests.exceptions.Timeout as e:
            # 超时
            self._resp = None
        except requests.exceptions.TooManyRedirects as e:
            self._resp = None
        except requests.exceptions.RequestException as e:
            self._resp = None
        else:
            if self._resp.status_code != 200:
                print('[HTTP] Return Code: ', self._resp.status_code)
                self._resp = None

        if self._resp is not None:
            return self._resp.content
        else:
            return None

    def http_timeout_get(self, url):
        return self._do_http_request('GET', url)

    def http_timeout_post(self, url, data, file=None):
        return self._do_http_request('POST', url, data, file)
