#!/usr/bin/env python
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


import os

from cyclozzo.apps.api import api_base_pb
from cyclozzo.apps.api import apiproxy_stub_map
from cyclozzo.apps.api.channel import channel_service_pb
from cyclozzo.apps.runtime import apiproxy_errors

MAX_DURATION = 60 * 60 * 4

MAX_SIMULTANEOUS_CONNECTIONS = 10


class Error(Exception):
  """Base error class for this module."""


class InvalidChannelKeyError(Error):
  """Error that indicates a bad channel id."""

class InvalidChannelKeyError(Error):
  """Error that indicates a bad channel key."""

class InvalidMessageError(Error):
  """Error that indicates a message is malformed."""


class ChannelTimeoutError(Error):
  """Error that indicates the given channel has timed out."""


def _ToChannelError(error):
  """Translate an application error to a channel Error, if possible.

  Args:
    error: An ApplicationError to translate.

  Returns:
    The appropriate channel service error, if a match is found, or the original
    ApplicationError.
  """
  error_map = {
      channel_service_pb.ChannelServiceError.INVALID_CHANNEL_KEY:
      InvalidChannelKeyError,
      channel_service_pb.ChannelServiceError.BAD_MESSAGE:
      InvalidMessageError,
      channel_service_pb.ChannelServiceError.CHANNEL_TIMEOUT:
      ChannelTimeoutError
      }

  if error.application_error in error_map:
    return error_map[error.application_error](error.error_detail)
  else:
    return error


def _GetService():
  """Gets the service name to use, based on if we're on the dev server."""
  if os.environ.get('SERVER_SOFTWARE', '').startswith('Devel'):
    return 'channel'
  else:
    return 'xmpp'


def create_channel(application_key):
  """Create a channel.

  Args:
    application_key: A key to identify this channel on the server side.

  Returns:
    A string id that the client can use to connect to the channel.

  Raises:
    InvalidChannelTimeoutError: if the specified timeout is invalid.
    Other errors returned by _ToChannelError
  """

  request = channel_service_pb.CreateChannelRequest()
  response = channel_service_pb.CreateChannelResponse()

  request.set_application_key(application_key)

  try:
    apiproxy_stub_map.MakeSyncCall('channel',#_GetService(),
                                   'CreateChannel',
                                   request,
                                   response)
  except apiproxy_errors.ApplicationError, e:
    raise _ToChannelError(e)

  return response.client_id()


def send_message(application_key, message):
  """Send a message to a channel.

  Args:
    application_key: The key passed to create_channel.
    message: A string representing the message to send.

  Raises:
    Errors returned by _ToChannelError
  """
  request = channel_service_pb.SendMessageRequest()
  response = api_base_pb.VoidProto()

  request.set_application_key(application_key)
  request.set_message(message)

  try:
    apiproxy_stub_map.MakeSyncCall('channel',#_GetService(),
                                   'SendChannelMessage',
                                   request,
                                   response)
  except apiproxy_errors.ApplicationError, e:
    raise _ToChannelError(e)
