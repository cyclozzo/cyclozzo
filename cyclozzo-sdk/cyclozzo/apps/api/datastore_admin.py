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

"""The Python datastore admin API for managing indices and schemas.
"""



from cyclozzo.apps.api import api_base_pb
from cyclozzo.apps.api import apiproxy_stub_map
from cyclozzo.apps.api import datastore
from cyclozzo.apps.api import datastore_errors
from cyclozzo.apps.api import datastore_types
from cyclozzo.apps.datastore import datastore_index
from cyclozzo.apps.datastore import datastore_pb
from cyclozzo.apps.runtime import apiproxy_errors

def GetSchema(_app=None, namespace=None, properties=True, start_kind=None,
              end_kind=None):
  """Infers an app's schema from the entities in the datastore.

  Note that the PropertyValue PBs in the returned EntityProtos are empty
  placeholders, so they may cause problems if you try to convert them to
  python values with e.g. datastore_types. In particular, user values will
  throw UserNotFoundError because their email and auth domain fields will be
  empty.

  Args:
    properties: boolean, whether to include property names and types
    start_kind, end_kind: optional range endpoints for the kinds to return,
      compared lexicographically
    namespace: string, specified namespace of schema to be fetched

  Returns:
    list of entity_pb.EntityProto, with kind and property names and types
  """
  req = datastore_pb.GetSchemaRequest()
  req.set_app(datastore_types.ResolveAppId(_app))
  namespace = datastore_types.ResolveNamespace(namespace)
  if namespace:
    req.set_name_space(namespace)
  req.set_properties(properties)
  if start_kind is not None:
    req.set_start_kind(start_kind)
  if end_kind is not None:
    req.set_end_kind(end_kind)
  resp = datastore_pb.Schema()

  resp = _Call('GetSchema', req, resp)
  return resp.kind_list()


def GetIndices(_app=None):
  """Fetches all composite indices in the datastore for this app.

  Returns:
    list of entity_pb.CompositeIndex
  """
  req = api_base_pb.StringProto()
  req.set_value(datastore_types.ResolveAppId(_app))
  resp = datastore_pb.CompositeIndices()
  resp = _Call('GetIndices', req, resp)
  return resp.index_list()


def CreateIndex(index):
  """Creates a new composite index in the datastore for this app.

  Args:
    index: entity_pb.CompositeIndex

  Returns:
    int, the id allocated to the index
  """
  resp = api_base_pb.Integer64Proto()
  resp = _Call('CreateIndex', index, resp)
  return resp.value()


def UpdateIndex(index):
  """Updates an index's status. The entire index definition must be present.

  Args:
    index: entity_pb.CompositeIndex
  """
  _Call('UpdateIndex', index, api_base_pb.VoidProto())


def DeleteIndex(index):
  """Deletes an index. The entire index definition must be present.

  Args:
    index: entity_pb.CompositeIndex
  """
  _Call('DeleteIndex', index, api_base_pb.VoidProto())


def _Call(call, req, resp):
  """Generic method for making a datastore API call.

  Args:
    call: string, the name of the RPC call
    req: the request PB. if the app_id field is not set, it defaults to the
      local app.
    resp: the response PB
  """
  if hasattr(req, 'app_id'):
    req.set_app_id(datastore_types.ResolveAppId(req.app_id()))

  try:
    result = apiproxy_stub_map.MakeSyncCall('datastore_v3', call, req, resp)
    if result:
      return result
    return resp
  except apiproxy_errors.ApplicationError, err:
    raise datastore._ToDatastoreError(err)



