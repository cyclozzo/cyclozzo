#!/usr/bin/env python
#
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

"""A NotImplemented Images API stub for when the PIL library is not found."""



class ImagesNotImplementedServiceStub(object):
  """Stub version of images API which raises a NotImplementedError."""

  def MakeSyncCall(self, service, call, request, response):
    """Main entry point.

    Args:
      service: str, must be 'images'.
      call: str, name of the RPC to make, must be part of ImagesService.
      request: pb object, corresponding args to the 'call' argument.
      response: pb object, return value for the 'call' argument.
    """
    raise NotImplementedError("Unable to find the Python PIL library.  Please "
                              "view the SDK documentation for details about "
                              "installing PIL on your system.")
