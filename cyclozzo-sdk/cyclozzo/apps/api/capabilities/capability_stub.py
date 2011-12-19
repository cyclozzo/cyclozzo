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

"""Stub version of the capability service API, everything is always enabled."""



from cyclozzo.apps.api import apiproxy_stub
from cyclozzo.apps.api import capabilities

IsEnabledRequest = capabilities.IsEnabledRequest
IsEnabledResponse = capabilities.IsEnabledResponse
CapabilityConfig = capabilities.CapabilityConfig

class CapabilityServiceStub(apiproxy_stub.APIProxyStub):
  """Python only capability service stub."""

  def __init__(self, service_name='capability_service'):
    """Constructor.

    Args:
      service_name: Service name expected for all calls.
    """
    super(CapabilityServiceStub, self).__init__(service_name)


  def _Dynamic_IsEnabled(self, request, response):
    """Implementation of CapabilityService::IsEnabled().

    Args:
      request: An IsEnabledRequest.
      response: An IsEnabledResponse.
    """
    response.set_summary_status(IsEnabledResponse.ENABLED)

    default_config = response.add_config()
    default_config.set_package('')
    default_config.set_capability('')
    default_config.set_status(CapabilityConfig.ENABLED)
