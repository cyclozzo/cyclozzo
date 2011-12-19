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

"""Define the DeadlineExceededError exception."""



try:
  BaseException
except NameError:
  BaseException = Exception


class DeadlineExceededError(BaseException):
  """Exception raised when the request reaches its overall time limit.

  Not to be confused with runtime.apiproxy_errors.DeadlineExceededError.
  That one is raised when individual API calls take too long.
  """
