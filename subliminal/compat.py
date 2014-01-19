# -*- coding: utf-8 -*-
import httplib
import xmlrpclib
import socket


class TimeoutTransport(xmlrpclib.Transport, object):
    def __init__(self, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, *args, **kwargs):
        super(TimeoutTransport, self).__init__(*args, **kwargs)
        self.timeout = timeout

    def make_connection(self, host):
        h = httplib.HTTPConnection(host, timeout=self.timeout)
        return h
