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

"""Temporary files.

This module is a replacement for the stock tempfile module in Python,
and provides only in-memory temporary files as implemented by
cStringIO. The only functionality provided is the TemporaryFile
function.
"""

try:
  from cStringIO import StringIO
except ImportError:
  from StringIO import StringIO

__all__ = [
  "TemporaryFile",

  "NamedTemporaryFile", "mkstemp", "mkdtemp", "mktemp",
  "TMP_MAX", "gettempprefix", "tempdir", "gettempdir",
]

TMP_MAX = 10000

template = "tmp"

tempdir = None

def TemporaryFile(mode='w+b', bufsize=-1, suffix="",
                  prefix=template, dir=None):
  """Create and return a temporary file.
  Arguments:
  'prefix', 'suffix', 'dir', 'mode', 'bufsize' are all ignored.

  Returns an object with a file-like interface.  The file is in memory
  only, and does not exist on disk.
  """

  return StringIO()

def PlaceHolder(*args, **kwargs):
  raise NotImplementedError("Only tempfile.TemporaryFile is available for use")

NamedTemporaryFile = PlaceHolder
mkstemp = PlaceHolder
mkdtemp = PlaceHolder
mktemp = PlaceHolder
gettempprefix = PlaceHolder
tempdir = PlaceHolder
gettempdir = PlaceHolder
