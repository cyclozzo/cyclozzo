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
"""Errors used in the urlfetch API
developers.
"""






class Error(Exception):
  """Base URL fetcher error type."""


class InvalidURLError(Error):
  """Raised when the URL given is empty or invalid.

  Only http: and https: URLs are allowed. The maximum URL length
  allowed is 2048 characters. The login/pass portion is not
  allowed. In deployed applications, only ports 80 and 443 for http
  and https respectively are allowed.
  """


class DownloadError(Error):
  """Raised when the we could not fetch the URL for any reason.

  Note that this exception is only raised when we could not contact the
  server. HTTP errors (e.g., 404) are returned in as the status_code field
  in the return value of Fetch, and no exception is raised.
  """


class ResponseTooLargeError(Error):
  """Raised when the response was too large and was truncated."""
  def __init__(self, response):
    self.response = response


class InvalidMethodError(Error):
  """Raised when an invalid value for 'method' is provided"""

