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

"""Errors used in the YAML API, which is used by app developers."""



class Error(Exception):
  """Base datastore yaml error type."""

class ProtocolBufferParseError(Error):
  """Error in protocol buffer parsing"""


class EmptyConfigurationFile(Error):
  """Tried to load empty configuration file."""


class MultipleConfigurationFile(Error):
  """Tried to load configuration file with multiple objects."""


class UnexpectedAttribute(Error):
  """Raised when an unexpected attribute is encounted."""


class DuplicateAttribute(Error):
  """Generated when an attribute is assigned to twice."""


class ListenerConfigurationError(Error):
  """Generated when there is a parsing problem due to configuration."""


class IllegalEvent(Error):
  """Raised when an unexpected event type is received by listener."""


class InternalError(Error):
  """Raised when an internal implementation error is detected."""


class EventListenerError(Error):
  """Top level exception raised by YAML listener.

  Any exception raised within the process of parsing a YAML file via an
  EventListener is caught and wrapped in an EventListenerError.  The causing
  exception is maintained, but additional useful information is saved which
  can be used for reporting useful information to users.

  Attributes:
    cause: The original exception which caused the EventListenerError.
  """

  def __init__(self, cause):
    """Initialize event-listener error."""
    if hasattr(cause, 'args') and cause.args:
      Error.__init__(self, *cause.args)
    else:
      Error.__init__(self, str(cause))
    self.cause = cause


class EventListenerYAMLError(EventListenerError):
  """Generated specifically for yaml.error.YAMLError."""


class EventError(EventListenerError):
  """Generated specifically when an error occurs in event handler.

  Attributes:
    cause: The original exception which caused the EventListenerError.
    event: Event being handled when exception occured.
  """

  def __init__(self, cause, event):
    """Initialize event-listener error."""
    EventListenerError.__init__(self, cause)
    self.event = event

  def __str__(self):
    return '%s\n%s' % (self.cause, self.event.start_mark)
