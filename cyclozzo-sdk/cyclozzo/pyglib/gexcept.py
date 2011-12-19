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

"""
Generic exceptions.
"""

class TimeoutException(Exception):
  def __init__(self, msg=""):
    Exception.__init__(self, msg)

class NestedException(Exception):
  def __init__(self, exc_info):
    Exception.__init__(self, exc_info[1])
    self.exc_info_ = exc_info
  def exc_info(self):
    return self.exc_info_

class AbstractMethod(Exception):
  """Raise this exception to indicate that a method is abstract.  Example:
        class Foo:
          def Bar(self):
            raise gexcept.AbstractMethod"""
  def __init__(self):
    Exception.__init__(self)
