# -*- coding: utf-8 -*-
#
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

from cyclozzo.apps.api import apiproxy_stub
from cyclozzo.apps.api.channel import channel_service_pb
from cyclozzo.apps.runtime import apiproxy_errors

import httplib
import logging
import random
import time

WEEKDAY_ABBR = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
MONTHNAME    = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def rfc1123_date(ts=None):
  """Return an RFC 1123 format date string.

  Required for use in HTTP Date headers per the HTTP 1.1 spec. 'Fri, 10 Nov
  2000 16:21:09 GMT'.
  """
  if ts is None: ts=time.time()
  year, month, day, hh, mm, ss, wd, y, z = time.gmtime(ts)
  return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (WEEKDAY_ABBR[wd],
                                                  day, MONTHNAME[month],
                                                  year,
                                                  hh, mm, ss)


class ChannelServiceStub(apiproxy_stub.APIProxyStub):
  """Channel service stub.

  Using a publish/subscribe service.
  """

  def __init__(self, address, log=logging.info, service_name='channel'):
    """Initializes the Channel API proxy stub.

    Args:
      address: The address of our Channel service.
      log: A logger, used for dependency injection.
      service_name: Service name expected for all calls.
    """
    apiproxy_stub.APIProxyStub.__init__(self, service_name)
    self._address = address
    self._log = log

  def _Dynamic_CreateChannel(self, request, response):
    """Implementation of channel.get_channel.

    Args:
      request: A ChannelServiceRequest.
      response: A ChannelServiceResponse
    """
    application_key = request.application_key()
    if not application_key:
      raise apiproxy_errors.ApplicationError(
          channel_service_pb.ChannelServiceError.INVALID_CHANNEL_KEY)

    response.set_client_id(application_key)

  def _Dynamic_SendChannelMessage(self, request, response):
    """Implementation of channel.send_message.

    Queues a message to be retrieved by the client when it polls.

    Args:
      request: A SendMessageRequest.
      response: A VoidProto.
    """
    application_key = request.application_key()

    if not request.message():
      raise apiproxy_errors.ApplicationError(
          channel_service_pb.ChannelServiceError.BAD_MESSAGE)

    conn = httplib.HTTPConnection(self._address)
    headers = {'Content-Type': 'text/plain',
               'Last-Modified': rfc1123_date()}
    conn.request("POST", "/_ah/publish?id=%s" %
                 application_key, request.message(), headers)
    conn.close()
