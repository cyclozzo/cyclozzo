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

"""Exceptions raised my mail API."""


class Error(Exception):
  """Base Mail error type."""

class BadRequestError(Error):
  """Email is not valid."""

class InvalidSenderError(Error):
  """Sender is not a permitted to send mail for this application."""

class InvalidEmailError(Error):
  """Bad email set on an email field."""

class InvalidAttachmentTypeError(Error):
  """Invalid file type for attachments.  We don't send viruses!"""

class MissingRecipientsError(Error):
  """No recipients specified in message."""

class MissingSenderError(Error):
  """No sender specified in message."""

class MissingSubjectError(Error):
  """Subject not specified in message."""

class MissingBodyError(Error):
  """No body specified in message."""

class PayloadEncodingError(Error):
  """Unknown payload encoding."""

class UnknownEncodingError(PayloadEncodingError):
  """Raised when encoding is not known."""

class UnknownCharsetError(PayloadEncodingError):
  """Raised when charset is not known."""
