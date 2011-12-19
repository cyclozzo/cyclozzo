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
"""Errors thrown by apiproxy.MakeSyncCall.
"""


class Error(Exception):
  """Base APIProxy error type."""


class RPCFailedError(Error):
  """Raised by APIProxy calls when the RPC to the application server fails."""


class CallNotFoundError(Error):
  """Raised by APIProxy calls when the requested method cannot be found."""


class ArgumentError(Error):
  """Raised by APIProxy calls if there is an error parsing the arguments."""


class DeadlineExceededError(Error):
  """Raised by APIProxy calls if the call took too long to respond."""


class CancelledError(Error):
  """Raised by APIProxy calls if the call was cancelled, such as when
  the user's request is exiting."""


class ApplicationError(Error):
  """Raised by APIProxy in the event of an application-level error."""
  def __init__(self, application_error, error_detail=''):
    self.application_error = application_error
    self.error_detail = error_detail
    Error.__init__(self, application_error)

  def __str__(self):
    return 'ApplicationError: %d %s' % (self.application_error,
                                        self.error_detail)

class OverQuotaError(Error):
  """Raised by APIProxy calls when they have been blocked due to a lack of
  available quota."""

class RequestTooLargeError(Error):
  """Raised by APIProxy calls if the request was too large."""

class CapabilityDisabledError(Error):
  """Raised by APIProxy when API calls are temporarily disabled."""

class FeatureNotEnabledError(Error):
  """Raised by APIProxy when the app must enable a feature to use this call."""

class InterruptedError(Error):
  """Raised by APIProxy.Wait() when the wait is interrupted by an uncaught
  exception from some callback, not necessarily associated with the RPC in
  question."""
  def __init__(self, exception, rpc):
    self.args = ("The Wait() request was interrupted by an exception from "
                 "another callback:", exception)
    self.__rpc = rpc
    self.__exception = exception

  @property
  def rpc(self):
    return self.__rpc

  @property
  def exception(self):
    return self.__exception
