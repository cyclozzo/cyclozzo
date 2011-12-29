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
#   Author: Sreejith K
#   Created on 20th Dec 2011

"""Asynchronous PubSub handlers using Redis for Channel API.
"""

import logging
import os
from json import loads, dumps
import threading

import tornado.web
import tornado.ioloop
import brukva


CHANNEL_JSAPI_PATTERN = '/_ah/channel/jsapi'
CHANNEL_PUBLISH_PATTERN = '/_ah/publish(?:/.*)?'
CHANNEL_SUBSCRIBE_PATTERN = '/_ah/subscribe(?:/.*)?'


class ChannelPublishHandler(tornado.web.RequestHandler):
    """Publish messages to a channel.
    """
    @tornado.web.asynchronous
    def post(self):
        """Handle the POST request for publishing a message.
        """
        channel_id = self.get_argument('id', None)
        channel_data = {}
        channel_data['message'] = self.request.body
        channel_data['content_type'] = self.request.headers.get('Content-Type')
        channel_data['last_modified'] = self.request.headers.get('Last-Modified')
        client = brukva.Client(port=6380)
        client.connect()
        tornado.ioloop.IOLoop().instance().add_callback(
            lambda: self.publish_message(client, channel_id, channel_data))

    def publish_message(self, client, channel_id, message):
        """Publish the message on Redis.
        """
        logging.debug('Publishing data on the channel %s' %channel_id)
        client.publish(channel_id, dumps(message))
        self.finish()


class ChannelSubscribeHandler(tornado.web.RequestHandler):
    """Push messages to clients asynchronously.
    """
    @tornado.web.asynchronous
    def get(self):
        """Subscribe to a channel.
        """
        channel_id = self.get_argument('id', None)
        logging.debug('GET: application key: %s' %channel_id)
        client = brukva.Client(port=6380)
        client.connect()
        logging.debug('subscribing to %s' %channel_id)
        client.subscribe([channel_id])
        client.listen(self.stream_channel_messages)

    def stream_channel_messages(self, message):
        """Callback method for incoming messages on the channel.
        """
        logging.debug('Message found on channel %s' %message.channel)
        channel_data = loads(message.body)
        logging.debug('Forwading Message: %r' %channel_data['message'])
        try:
            self.write(channel_data['message'])
            self.flush()
        except:
            #FIXME finish the request on client disconnection
            log.info('closing channel %s' %message.channel)
            self.finish()


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


def main():
    logging.basicConfig(level=logging.DEBUG)
    application = tornado.web.Application([
        (CHANNEL_SUBSCRIBE_PATTERN, ChannelSubscribeHandler),
        (CHANNEL_PUBLISH_PATTERN, ChannelPublishHandler),
    ])
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
