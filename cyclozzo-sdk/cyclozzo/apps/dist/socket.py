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


AF_INET = None
SOCK_STREAM = None
SOCK_DGRAM = None

_GLOBAL_DEFAULT_TIMEOUT = object()


class error(OSError):
  pass

class herror(error):
  pass

class gaierror(error):
  pass

class timeout(error):
  pass


def _fileobject(fp, mode='rb', bufsize=-1, close=False):
  """Assuming that the argument is a StringIO or file instance."""
  if not hasattr(fp, 'fileno'):
    fp.fileno = lambda: None
  return fp

ssl = None
