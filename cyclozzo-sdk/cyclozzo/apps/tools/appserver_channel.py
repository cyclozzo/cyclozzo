# -*- coding: utf-8 -*-
#
#!/usr/bin/env python
#
#   Copyright (C) 2010-2011 Stackless Recursion
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2, or (at your option)
#   any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
"""Implementation of request handlers providing PubSub functionalities and JSAPI."""

import logging
import os

import tornado.web
import tornado.auth
import tornado.wsgi


CHANNEL_JSAPI_PATTERN = '/_ah/channel/jsapi'
CHANNEL_PUBLISH_PATTERN = '/_ah/publish(?:/.*)?'
CHANNEL_SUBSCRIBE_PATTERN = '/_ah/subscribe(?:/.*)?'


class ChannelPublishHandler(tornado.web.RequestHandler):
    """Publish messages for a channel.
    """
    @tornado.web.asynchronous
    def post(self):
        application_key = self.get_argument('id', None)
        message = self.request.body


class ChannelSubscribeHandler(tornado.web.RequestHandler):
    """Push messages to clients asynchronously.
    """
    @tornado.web.asynchronous
    def get(self):
        pass


class ChannelJSAPIHandler(tornado.web.RequestHandler):
    """Channel JSAPI handler.
    """
    def get(self):
        js_file = open(
            os.path.join(os.path.dirname(__file__), 'cyclozzo-channel-js.js'), 'rb')
        js_data = js_file.read()
        js_file.close()
        self.set_header('Content-Type', 'application/javascript')
        self.write(js_data)


