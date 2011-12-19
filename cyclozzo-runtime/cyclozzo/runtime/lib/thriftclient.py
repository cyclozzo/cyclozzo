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
from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from cyclozzo.hyperthrift.gen2 import HqlService

class ThriftClient(HqlService.Client):
  def __init__(self, host, port, timeout_ms = 300000, do_open = 1):
    socket = TSocket.TSocket(host, port)
    socket.setTimeout(timeout_ms)
    self.transport = TTransport.TFramedTransport(socket)
    protocol = TBinaryProtocol.TBinaryProtocol(self.transport)
    HqlService.Client.__init__(self, protocol)

    if do_open:
      self.open(timeout_ms)

  def open(self, timeout_ms):
    self.transport.open()
    self.do_close = 1

  def close(self):
    if self.do_close:
      self.transport.close()
