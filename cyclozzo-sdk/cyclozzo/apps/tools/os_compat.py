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
"""OS cross-platform compatibility tweaks.

This module will, on import, change some parts of the running evironment so
that other modules do not need special handling when running on different
operating systems, such as Linux/Mac OSX/Windows.

Some of these changes must be done before other modules are imported, so
always import this module first.
"""


import os
os.environ['TZ'] = 'UTC'
import time
if hasattr(time, 'tzset'):
  time.tzset()

import __builtin__


if 'WindowsError' in __builtin__.__dict__:
  WindowsError = WindowsError
else:
  class WindowsError(Exception):
    """A fake Windows Error exception which should never be thrown."""


ERROR_PATH_NOT_FOUND = 3
ERROR_ACCESS_DENIED = 5
ERROR_ALREADY_EXISTS = 183
