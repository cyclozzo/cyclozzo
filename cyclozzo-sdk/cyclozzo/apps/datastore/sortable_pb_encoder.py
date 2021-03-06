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

"""An Encoder class for Protocol Buffers that preserves sorting characteristics.

This is used by datastore_sqlite_stub in order to index entities in a fashion
that preserves the datastore's sorting semantics. Broadly, there are four
changes from regular PB encoding:

 - Strings are escaped and null terminated instead of length-prefixed. The
   escaping replaces \0 with \1\1 and \1 with \1\2, thus preserving the ordering
   of the original string.
 - Variable length integers are encoded using a variable length encoding that
   preserves order. The first byte stores the absolute value if it's between
   -119 to 119, otherwise it stores the number of bytes that follow.
 - Numbers are stored big endian instead of little endian.
 - Negative doubles are entirely negated, while positive doubles have their sign
   bit flipped.

Warning:
  Due to the way nested Protocol Buffers are encoded, this encoder will NOT
  preserve sorting characteristics for embedded protocol buffers!
"""







import array
import struct

from cyclozzo.net.proto import ProtocolBuffer


_MAX_UNSIGNED_BYTE = 255

_MAX_LONG_BYTES = 8

_MAX_INLINE = (_MAX_UNSIGNED_BYTE - (2 * _MAX_LONG_BYTES)) / 2
_MIN_INLINE = -_MAX_INLINE
_OFFSET = 1 + 8
_POS_OFFSET = _OFFSET + _MAX_INLINE * 2


class Encoder(ProtocolBuffer.Encoder):
  """Encodes Protocol Buffers in a form that sorts nicely."""

  def put16(self, value):
    if value < 0 or value >= (1<<16):
      raise ProtocolBuffer.ProtocolBufferEncodeError, 'u16 too big'
    self.buf.append((value >> 8) & 0xff)
    self.buf.append((value >> 0) & 0xff)
    return

  def put32(self, value):
    if value < 0 or value >= (1L<<32):
      raise ProtocolBuffer.ProtocolBufferEncodeError, 'u32 too big'
    self.buf.append((value >> 24) & 0xff)
    self.buf.append((value >> 16) & 0xff)
    self.buf.append((value >> 8) & 0xff)
    self.buf.append((value >> 0) & 0xff)
    return

  def put64(self, value):
    if value < 0 or value >= (1L<<64):
      raise ProtocolBuffer.ProtocolBufferEncodeError, 'u64 too big'
    self.buf.append((value >> 56) & 0xff)
    self.buf.append((value >> 48) & 0xff)
    self.buf.append((value >> 40) & 0xff)
    self.buf.append((value >> 32) & 0xff)
    self.buf.append((value >> 24) & 0xff)
    self.buf.append((value >> 16) & 0xff)
    self.buf.append((value >> 8) & 0xff)
    self.buf.append((value >> 0) & 0xff)
    return

  def _PutVarInt(self, value):
    if value is None:
      self.buf.append(0)
      return

    if value >= _MIN_INLINE and value <= _MAX_INLINE:
      value = _OFFSET + (value - _MIN_INLINE)
      self.buf.append(value & 0xff)
      return

    negative = False

    if value < 0:
      value = _MIN_INLINE - value
      negative = True
    else:
      value = value - _MAX_INLINE

    len = 0
    w = value
    while w > 0:
      w >>= 8
      len += 1

    if negative:
      head = _OFFSET - len
    else:
      head = _POS_OFFSET + len
    self.buf.append(head & 0xff)

    for i in range(len - 1, -1, -1):
      b = value >> (i * 8)
      if negative:
        b = _MAX_UNSIGNED_BYTE - (b & 0xff)
      self.buf.append(b & 0xff)

  def putVarInt32(self, value):
    if value >= 0x80000000 or value < -0x80000000:
      raise ProtocolBuffer.ProtocolBufferEncodeError, 'int32 too big'
    self._PutVarInt(value)

  def putVarInt64(self, value):
    if value >= 0x8000000000000000 or value < -0x8000000000000000:
      raise ProtocolBuffer.ProtocolBufferEncodeError, 'int64 too big'
    self._PutVarInt(value)

  def putVarUint64(self, value):
    if value < 0 or value >= 0x10000000000000000:
      raise ProtocolBuffer.ProtocolBufferEncodeError, 'uint64 too big'
    self._PutVarInt(value)

  def putFloat(self, value):
    encoded = array.array('B')
    encoded.fromstring(struct.pack('>f', value))
    if value < 0:
      encoded[0] ^= 0xFF
      encoded[1] ^= 0xFF
      encoded[2] ^= 0xFF
      encoded[3] ^= 0xFF
    else:
      encoded[0] ^= 0x80
    self.buf.extend(encoded)

  def putDouble(self, value):
    encoded = array.array('B')
    encoded.fromstring(struct.pack('>d', value))
    if value < 0:
      encoded[0] ^= 0xFF
      encoded[1] ^= 0xFF
      encoded[2] ^= 0xFF
      encoded[3] ^= 0xFF
      encoded[4] ^= 0xFF
      encoded[5] ^= 0xFF
      encoded[6] ^= 0xFF
      encoded[7] ^= 0xFF
    else:
      encoded[0] ^= 0x80
    self.buf.extend(encoded)

  def putPrefixedString(self, value):
    self.buf.fromstring(value.replace('\1', '\1\2').replace('\0', '\1\1') + '\0')


class Decoder(ProtocolBuffer.Decoder):
  def __init__(self, buf, idx=0, limit=None):
    if not limit:
      limit = len(buf)
    ProtocolBuffer.Decoder.__init__(self, buf, idx, limit)

  def get16(self):
    if self.idx + 2 > self.limit:
      raise ProtocolBuffer.ProtocolBufferDecodeError, 'truncated'
    c = self.buf[self.idx]
    d = self.buf[self.idx + 1]
    self.idx += 2
    return (c << 8) | d

  def get32(self):
    if self.idx + 4 > self.limit:
      raise ProtocolBuffer.ProtocolBufferDecodeError, 'truncated'
    c = long(self.buf[self.idx])
    d = self.buf[self.idx + 1]
    e = self.buf[self.idx + 2]
    f = self.buf[self.idx + 3]
    self.idx += 4
    return (c << 24) | (d << 16) | (e << 8) | f

  def get64(self):
    if self.idx + 8 > self.limit:
      raise ProtocolBuffer.ProtocolBufferDecodeError, 'truncated'
    c = long(self.buf[self.idx])
    d = long(self.buf[self.idx + 1])
    e = long(self.buf[self.idx + 2])
    f = long(self.buf[self.idx + 3])
    g = long(self.buf[self.idx + 4])
    h = self.buf[self.idx + 5]
    i = self.buf[self.idx + 6]
    j = self.buf[self.idx + 7]
    self.idx += 8
    return ((c << 56) | (d << 48) | (e << 40) | (f << 32) | (g << 24)
            | (h << 16) | (i << 8) | j)

  def getVarInt64(self):
    b = self.get8()
    if b >= _OFFSET and b <= _POS_OFFSET:
      return b - _OFFSET + _MIN_INLINE
    if b == 0:
      return None

    if b < _OFFSET:
      negative = True
      bytes = _OFFSET - b
    else:
      negative = False
      bytes = b - _POS_OFFSET

    ret = 0
    for i in range(bytes):
      b = self.get8()
      if negative:
        b = _MAX_UNSIGNED_BYTE - b
      ret = ret << 8 | b

    if negative:
      return _MIN_INLINE - ret
    else:
      return ret + _MAX_INLINE

  def getVarInt32(self):
    result = self.getVarInt64()
    if result >= 0x80000000L or result < -0x80000000L:
      raise ProtocolBuffer.ProtocolBufferDecodeError, 'corrupted'
    return result

  def getVarUint64(self):
    result = self.getVarInt64()
    if result < 0:
      raise ProtocolBuffer.ProtocolBufferDecodeError, 'corrupted'
    return result

  def getFloat(self):
    if self.idx + 4 > self.limit:
      raise ProtocolBuffer.ProtocolBufferDecodeError, 'truncated'
    a = self.buf[self.idx:self.idx+4]
    self.idx += 4
    if a[0] & 0x80:
      a[0] ^= 0x80
    else:
      a = [x ^ 0xFF for x in a]
    return struct.unpack('>f', array.array('B', a).tostring())[0]

  def getDouble(self):
    if self.idx + 8 > self.limit:
      raise ProtocolBuffer.ProtocolBufferDecodeError, 'truncated'
    a = self.buf[self.idx:self.idx+8]
    self.idx += 8
    if a[0] & 0x80:
      a[0] ^= 0x80
    else:
      a = [x ^ 0xFF for x in a]
    return struct.unpack('>d', array.array('B', a).tostring())[0]

  def getPrefixedString(self):
    end_idx = self.idx
    while self.buf[end_idx] != 0:
      end_idx += 1

    data = array.array('B', self.buf[self.idx:end_idx]).tostring()
    self.idx = end_idx + 1
    return data.replace('\1\1', '\0').replace('\1\2', '\1')
