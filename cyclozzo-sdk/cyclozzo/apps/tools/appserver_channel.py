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
"""Asynchronous PubSub handlers using Redis for Channel API.
"""

import logging
import os
from json import loads, dumps

import tornado.web
import tornado.ioloop
import redis


CHANNEL_JSAPI_PATTERN = '/_ah/channel/jsapi'
CHANNEL_PUBLISH_PATTERN = '/_ah/publish(?:/.*)?'
CHANNEL_SUBSCRIBE_PATTERN = '/_ah/subscribe(?:/.*)?'


class ChannelPublishHandler(tornado.web.RequestHandler):
    """Publish messages to a channel.
    """
    @tornado.web.asynchronous
    def post(self):
        application_key = self.get_argument('id', None)
        channel_data = {}
        channel_data['message'] = self.request.body
        channel_data['content_type'] = self.request.headers.get('Content-Type')
        channel_data['last_modified'] = self.request.headers.get('Last-Modified')
        rc = redis.Redis()
        rc.publish(application_key, dumps(channel_data))
        self.finish()


class ChannelSubscribeHandler(tornado.web.RequestHandler):
    """Push messages to clients asynchronously.
    """
    @tornado.web.asynchronous
    def get(self):
        """Subscribe to a channel.
        """
        application_key = self.get_argument('id', None)
        rc = redis.Redis()
        ps = rc.pubsub()
        ps.subscribe([application_key])
        self.stream_channel_messages(ps)

    @self.async_callback
    def stream_channel_messages(self, pubsub):
        """A long polling subscribe method.
        """
        for item in pubsub.listen():
            if item['type'] == 'message':
                channel_data = loads(item['data']['message'])
                self.write(channel_data)
                return self.finish()


class ChannelJSAPIHandler(tornado.web.RequestHandler):
    """Channel JSAPI handler.
    """
    def get(self):
        """Returns the JSAPI script.
        """
        js_file = open(
            os.path.join(os.path.dirname(__file__), 'cyclozzo-channel-js.js'), 'rb')
        js_data = js_file.read()
        js_file.close()
        self.set_header('Content-Type', 'application/javascript')
        self.write(js_data)


