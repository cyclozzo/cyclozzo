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
This is the Python counterpart to the RawMessage class defined in rawmessage.h.

To use this, put the following line in your .proto file:

python from google.net.proto.RawMessage import RawMessage

"""

__pychecker__ = 'no-callinit no-argsused'

from google.net.proto import ProtocolBuffer

class RawMessage(ProtocolBuffer.ProtocolMessage):
  """
  This is a special subclass of ProtocolMessage that doesn't interpret its data
  in any way. Instead, it just stores it in a string.

  See rawmessage.h for more details.
  """

  def __init__(self, initial=None):
    self.__contents = ''
    if initial is not None:
      self.MergeFromString(initial)

  def contents(self):
    return self.__contents

  def set_contents(self, contents):
    self.__contents = contents

  def Clear(self):
    self.__contents = ''

  def IsInitialized(self, debug_strs=None):
    return 1

  def __str__(self, prefix="", printElemNumber=0):
    return prefix + self.DebugFormatString(self.__contents)

  def OutputUnchecked(self, e):
    e.putRawString(self.__contents)

  def TryMerge(self, d):
    self.__contents = d.getRawString()

  def MergeFrom(self, pb):
    assert pb is not self
    if pb.__class__ != self.__class__:
      return 0
    self.__contents = pb.__contents
    return 1

  def Equals(self, pb):
    return self.__contents == pb.__contents

  def __eq__(self, other):
    return (other is not None) and (other.__class__ == self.__class__) and self.Equals(other)

  def __ne__(self, other):
    return not (self == other)

  def ByteSize(self):
    return len(self.__contents)

