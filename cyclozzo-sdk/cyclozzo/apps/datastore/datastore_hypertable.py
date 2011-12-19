#! /usr/bin/env python
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
# Datastore implementation for Hypertable.
#	It should be registered by 
#		apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', HypertableStub())
#
# @author: Sreejith K
# Created on 27th March 2010

import logging
import cPickle as pickle
import ht
import threading
import datetime

from cyclozzo.apps.api import apiproxy_stub
from cyclozzo.apps.api import datastore, datastore_types, datastore_errors, users
from cyclozzo.apps.datastore import datastore_pb, entity_pb

log = logging.getLogger(__name__)

_MAXIMUM_RESULTS = 1000
_MAX_QUERY_OFFSET = 1000
_MAX_QUERY_COMPONENTS = 100
_BATCH_SIZE = 20
_MAX_ACTIONS_PER_TXN = 5
_CURSOR_CONCAT_STR = '!CURSOR!'


class _Cursor(object):
  """A query cursor.

  Public properties:
    cursor: the integer cursor
    count: the original total number of results
    keys_only: whether the query is keys_only
    app: the app for which this cursor was created

  Class attributes:
    _next_cursor: the next cursor to allocate
    _next_cursor_lock: protects _next_cursor
  """
  _next_cursor = 1
  _next_cursor_lock = threading.Lock()

  def __init__(self, query, results, order_compare_entities):
    """Constructor.

    Args:
      query: the query request proto
      # the query results, in order, such that results[self.offset+1] is
      # the next result
      results: list of datastore.Entity
      order_compare_entities: a __cmp__ function for datastore.Entity that
        follows sort order as specified by the query
    """

    if query.has_compiled_cursor() and query.compiled_cursor().position_list():
      (self.__last_result, inclusive) = self._DecodeCompiledCursor(
          query, query.compiled_cursor())
      start_cursor_position = _Cursor._GetCursorOffset(results,
                                                       self.__last_result,
                                                       inclusive,
                                                       order_compare_entities)
    else:
      self.__last_result = None
      start_cursor_position = 0

    if query.has_end_compiled_cursor():
      (end_cursor_entity, inclusive) = self._DecodeCompiledCursor(
          query, query.end_compiled_cursor())
      end_cursor_position = _Cursor._GetCursorOffset(results,
                                                     end_cursor_entity,
                                                     inclusive,
                                                     order_compare_entities)
    else:
      end_cursor_position = len(results)

    results = results[start_cursor_position:end_cursor_position]

    if query.has_limit():
      limit = query.limit()
      if query.offset():
        limit += query.offset()
      if limit > 0 and limit < len(results):
        results = results[:limit]

    self.__results = results
    self.__query = query
    self.__offset = 0

    self.app = query.app()
    self.keys_only = query.keys_only()
    self.count = len(self.__results)
    self.cursor = self._AcquireCursorID()

  def _AcquireCursorID(self):
    """Acquires the next cursor id in a thread safe manner.
    """
    self._next_cursor_lock.acquire()
    try:
      cursor_id = _Cursor._next_cursor
      _Cursor._next_cursor += 1
    finally:
      self._next_cursor_lock.release()
    return cursor_id

  @staticmethod
  def _GetCursorOffset(results, cursor_entity, inclusive, compare):
    """Converts a cursor entity into a offset into the result set even if the
    cursor_entity no longer exists.

    Args:
      cursor_entity: the decoded datastore.Entity from the compiled query
      inclusive: boolean that specifies if to offset past the cursor_entity
      compare: a function that takes two datastore.Entity and compares them
    Returns:
      the integer offset
    """
    lo = 0
    hi = len(results)
    if inclusive:
      while lo < hi:
        mid = (lo + hi) // 2
        if compare(results[mid], cursor_entity) < 0:
          lo = mid + 1
        else:
          hi = mid
    else:
      while lo < hi:
        mid = (lo + hi) // 2
        if compare(cursor_entity, results[mid]) < 0:
          hi = mid
        else:
          lo = mid + 1
    return lo

  def _ValidateQuery(self, query, query_info):
    """Ensure that the given query matches the query_info.

    Args:
      query: datastore_pb.Query instance we are chacking
      query_info: datastore_pb.Query instance we want to match

    Raises BadRequestError on failure.
    """
    error_msg = 'Cursor does not match query: %s'
    exc = datastore_errors.BadRequestError
    if query_info.filter_list() != query.filter_list():
      raise exc(error_msg % 'filters do not match')
    if query_info.order_list() != query.order_list():
      raise exc(error_msg % 'orders do not match')

    for attr in ('ancestor', 'kind', 'name_space', 'search_query'):
      query_info_has_attr = getattr(query_info, 'has_%s' % attr)
      query_info_attr = getattr(query_info, attr)
      query_has_attr = getattr(query, 'has_%s' % attr)
      query_attr = getattr(query, attr)
      if query_info_has_attr():
        if not query_has_attr() or query_info_attr() != query_attr():
          raise exc(error_msg % ('%s does not match' % attr))
      elif query_has_attr():
        raise exc(error_msg % ('%s does not match' % attr))

  def _MinimalQueryInfo(self, query):
    """Extract the minimal set of information for query matching.

    Args:
      query: datastore_pb.Query instance from which to extract info.

    Returns:
      datastore_pb.Query instance suitable for matching against when
      validating cursors.
    """
    query_info = datastore_pb.Query()
    query_info.set_app(query.app())

    for filter in query.filter_list():
      query_info.filter_list().append(filter)
    for order in query.order_list():
      query_info.order_list().append(order)

    if query.has_ancestor():
      query_info.mutable_ancestor().CopyFrom(query.ancestor())

    for attr in ('kind', 'name_space', 'search_query'):
      query_has_attr = getattr(query, 'has_%s' % attr)
      query_attr = getattr(query, attr)
      query_info_set_attr = getattr(query_info, 'set_%s' % attr)
      if query_has_attr():
        query_info_set_attr(query_attr())

    return query_info

  def _MinimalEntityInfo(self, entity_proto, query):
    """Extract the minimal set of information that preserves entity order.

    Args:
      entity_proto: datastore_pb.EntityProto instance from which to extract
      information
      query: datastore_pb.Query instance for which ordering must be preserved.

    Returns:
      datastore_pb.EntityProto instance suitable for matching against a list of
      results when finding cursor positions.
    """
    entity_info = datastore_pb.EntityProto();
    order_names = [o.property() for o in query.order_list()]
    entity_info.mutable_key().MergeFrom(entity_proto.key())
    entity_info.mutable_entity_group().MergeFrom(entity_proto.entity_group())
    for prop in entity_proto.property_list():
      if prop.name() in order_names:
        entity_info.add_property().MergeFrom(prop)
    return entity_info;

  def _DecodeCompiledCursor(self, query, compiled_cursor):
    """Converts a compiled_cursor into a cursor_entity.

    Returns:
      (cursor_entity, inclusive): a datastore.Entity and if it should be
      included in the result set.
    """
    assert len(compiled_cursor.position_list()) == 1

    position = compiled_cursor.position(0)
    entity_pb = datastore_pb.EntityProto()
    (query_info_encoded, entity_encoded) = position.start_key().split(
        _CURSOR_CONCAT_STR, 1)
    query_info_pb = datastore_pb.Query()
    query_info_pb.ParseFromString(query_info_encoded)
    self._ValidateQuery(query, query_info_pb)

    entity_pb.ParseFromString(entity_encoded)
    return (datastore.Entity._FromPb(entity_pb, True),
            position.start_inclusive())

  def _EncodeCompiledCursor(self, query, compiled_cursor):
    """Converts the current state of the cursor into a compiled_cursor

    Args:
      query: the datastore_pb.Query this cursor is related to
      compiled_cursor: an empty datstore_pb.CompiledCursor
    """
    if self.__last_result is not None:
      position = compiled_cursor.add_position()
      query_info = self._MinimalQueryInfo(query)
      entity_info = self._MinimalEntityInfo(self.__last_result.ToPb(), query)
      start_key = _CURSOR_CONCAT_STR.join((
          query_info.Encode(),
          entity_info.Encode()))
      position.set_start_key(str(start_key))
      position.set_start_inclusive(False)

  def PopulateQueryResult(self, result, count, offset, compile=False):
    """Populates a QueryResult with this cursor and the given number of results.

    Args:
      result: datastore_pb.QueryResult
      count: integer of how many results to return
      offset: integer of how many results to skip
      compile: boolean, whether we are compiling this query
    """
    offset = min(offset, self.count - self.__offset)
    limited_offset = min(offset, _MAX_QUERY_OFFSET)
    if limited_offset:
      self.__offset += limited_offset
      result.set_skipped_results(limited_offset)

    if offset == limited_offset and count:
      if count > _MAXIMUM_RESULTS:
        count = _MAXIMUM_RESULTS
      results = self.__results[self.__offset:self.__offset + count]
      count = len(results)
      self.__offset += count
      result.result_list().extend(r._ToPb() for r in results)

    if self.__offset:
      self.__last_result = self.__results[self.__offset - 1]

    result.mutable_cursor().set_app(self.app)
    result.mutable_cursor().set_cursor(self.cursor)
    result.set_keys_only(self.keys_only)
    result.set_more_results(self.__offset < self.count)
    if compile:
      self._EncodeCompiledCursor(
          self.__query, result.mutable_compiled_cursor())


class HypertableStub(apiproxy_stub.APIProxyStub):

	_PROPERTY_TYPE_TAGS = {
		datastore_types.Blob: entity_pb.PropertyValue.kstringValue,
		bool: entity_pb.PropertyValue.kbooleanValue,
		datastore_types.Category: entity_pb.PropertyValue.kstringValue,
		datetime.datetime: entity_pb.PropertyValue.kint64Value,
		datastore_types.Email: entity_pb.PropertyValue.kstringValue,
		float: entity_pb.PropertyValue.kdoubleValue,
		datastore_types.GeoPt: entity_pb.PropertyValue.kPointValueGroup,
		datastore_types.IM: entity_pb.PropertyValue.kstringValue,
		int: entity_pb.PropertyValue.kint64Value,
		datastore_types.Key: entity_pb.PropertyValue.kReferenceValueGroup,
		datastore_types.Link: entity_pb.PropertyValue.kstringValue,
		long: entity_pb.PropertyValue.kint64Value,
		datastore_types.PhoneNumber: entity_pb.PropertyValue.kstringValue,
		datastore_types.PostalAddress: entity_pb.PropertyValue.kstringValue,
		datastore_types.Rating: entity_pb.PropertyValue.kint64Value,
		str: entity_pb.PropertyValue.kstringValue,
		datastore_types.Text: entity_pb.PropertyValue.kstringValue,
		type(None): 0,
		unicode: entity_pb.PropertyValue.kstringValue,
		users.User: entity_pb.PropertyValue.kUserValueGroup,
   	 }


	def __init__(self, app_id, ht_config='/etc/cyclozzo/hypertable.cfg', service_name='datastore_v3'):
		"""
		Initialize this stub with the service name.
		"""
		self._app_id = app_id
		self._client = ht.Client(ht_config)
		self.__queries = {}
		super(HypertableStub, self).__init__(service_name)

	def _Create_Obj_Datastore(self, entity):
		table_name = str('%s_%s' % (self._app_id, entity.kind()))
		try:
			if not self._app_id or len(self._app_id) == 0:
				raise app.NotSignedInError('App id is empty or invalid')
			table = self._client.open_table(table_name)
		except RuntimeError:
			self._client.hql('create table \'%s\' (app, props)' %table_name)
			log.debug('creating hypertable %s_%s' % (self._app_id, entity.kind()))

	def _Dynamic_Put(self, put_request, put_response):
		#FIXME: since we are getting protobuf-encoded entities here
		entities = [datastore.Entity.FromPb(entity) for entity in put_request.entity_list()]
		log.debug('entities to store: %r' %entities)
		# TODO: do the hypertable put operation here
		log.debug('writing %s entities' % len(entities))
		kind_cells_dict = {}
		for e in entities:
			# create table for this kind if not created already.
			self._Create_Obj_Datastore(e)

			if kind_cells_dict.has_key(e.kind()):
				kind_cells_dict[e.kind()].append(e)
			else:
				kind_cells_dict[e.kind()] = [e]

		put_keys = []
		for kind in kind_cells_dict.keys():
			table_name = str('%s_%s' % (self._app_id, kind))
			table = self._client.open_table(table_name)
			mutator = table.create_mutator()

			entities = kind_cells_dict[kind]
			for e in entities:
				# set kind information
				mutator.set(str(e.key()), 'app', 'type', str(e.kind()))
				mutator.flush()
				for name in e.keys():
					mutator.set(str(e.key()), 'props', str(name), pickle.dumps(e[name]))
					mutator.flush()
				#FIXME: as datastore.Put is expecting protobuf-encoded keys
				put_keys.append(e.key()._ToPb())
		log.debug('done.')
		put_response.key_list().extend(put_keys)

	
	def _Dynamic_Delete(self, delete_request, delete_response):
		#FIXME: since we are getting protobuf-encoded keys here
		keys = [datastore_types.Key._FromPb(key) for key in delete_request.key_list()]
		log.debug('deleting %s entities' % len(keys))
		kind_keys_dict = {}
		for key in keys:
			if kind_keys_dict.has_key(key.kind()):
				kind_keys_dict[key.kind()].append(key)
			else:
				kind_keys_dict[key.kind()] = [key]

		for kind in kind_keys_dict:
			table_name = str('%s_%s' % (self._app_id, kind))
			table = self._client.open_table(table_name)
			this_kind_keys = [str(key) for key in kind_keys_dict[kind]]
			for this_key in this_kind_keys:
				log.debug('deleting cells with key: %s' %this_key)
				#FIXME: mutator doesn't support deletion only with keys
				#mutator = table.create_mutator()
				# delete cells with this key
				#mutator.set_delete(this_key, 'app', '')
				#mutator.set_delete(this_key, 'props', '')
				self._client.hql('delete * from \'%s\' where row=\"%s\"' %(table_name, this_key))
	
	def _Dynamic_Get(self, get_request, get_response):
		#FIXME: since we are getting protobuf-encoded keys here
		keys = [datastore_types.Key._FromPb(key) for key in get_request.key_list()]
		kind_keys_dict = {}
		for key in keys:
			if kind_keys_dict.has_key(key.kind()):
				kind_keys_dict[key.kind()].append(key)
			else:
				kind_keys_dict[key.kind()] = [key]
		
		entities = []
		for kind in kind_keys_dict:
			table_name = str('%s_%s' % (self._app_id, kind))
			table = self._client.open_table(table_name)
			for key in kind_keys_dict[kind]:
				scan_spec_builder = ht.ScanSpecBuilder()
				scan_spec_builder.add_row_interval(str(key), True, str(key), True)
				scan_spec_builder.set_max_versions(1)
				scan_spec_builder.set_row_limit(0)
				total_cells = [cell for cell in table.create_scanner(scan_spec_builder)]
				# make cells with same keys as a single entity
				entity = datastore.Entity(kind, _app=self._app_id, name=key.name(), id=key.id())
				for cell in total_cells:
					if cell.column_family == 'props':
						entity[cell.column_qualifier] = pickle.loads(cell.value)
				group = get_response.add_entity()
				#FIXME: as datastore.Get is expecting a protobuf-encoded entities
				group.mutable_entity().CopyFrom(entity.ToPb())
	
	def _Dynamic_RunQuery(self, query, query_result):
		kind = query.kind()
		keys_only = query.keys_only()
		filters = query.filter_list()
		orders = query.order_list()
		offset = query.offset()
		limit = query.limit()
		namespace = query.name_space()
		#predicate = query.predicate()
		
		table_name = str('%s_%s' % (self._app_id, kind))
		table = self._client.open_table(table_name)
		scan_spec_builder = ht.ScanSpecBuilder()
		scan_spec_builder.set_max_versions(1)
		if filters or orders:
			scan_spec_builder.set_row_limit(0)
		else:
			scan_spec_builder.set_row_limit(offset + limit)
		# get the hypertable cells
		total_cells = [cell for cell in table.create_scanner(scan_spec_builder)]
		
		# make a cell-key dictionary
		key_cell_dict = {}
		for cell in total_cells:
			if key_cell_dict.has_key(cell.row_key):
				key_cell_dict[cell.row_key].append(cell)
			else:
				key_cell_dict[cell.row_key] = [cell]
		
		results = []
		for key in key_cell_dict:
			key_obj = datastore_types.Key(encoded=key)
			entity = datastore.Entity(kind, _app=self._app_id, name=key_obj.name(), id=key_obj.id())
			for cell in key_cell_dict[key]:
				if cell.column_family == 'props':
					entity[cell.column_qualifier] = pickle.loads(cell.value)
			results.append(entity)
	
		query.set_app(self._app_id)
		datastore_types.SetNamespace(query, namespace)
		encoded = datastore_types.EncodeAppIdNamespace(self._app_id, namespace)
	
		operators = {datastore_pb.Query_Filter.LESS_THAN:			 '<',
					 datastore_pb.Query_Filter.LESS_THAN_OR_EQUAL:	'<=',
					 datastore_pb.Query_Filter.GREATER_THAN:			'>',
					 datastore_pb.Query_Filter.GREATER_THAN_OR_EQUAL: '>=',
					 datastore_pb.Query_Filter.EQUAL:				 '==',
					 }
	
		def has_prop_indexed(entity, prop):
			"""Returns True if prop is in the entity and is indexed."""
			if prop in datastore_types._SPECIAL_PROPERTIES:
				return True
			elif prop in entity.unindexed_properties():
				return False
	
			values = entity.get(prop, [])
			if not isinstance(values, (tuple, list)):
				values = [values]
	
			for value in values:
				if type(value) not in datastore_types._RAW_PROPERTY_TYPES:
					return True
			return False
	
		for filt in filters:
			assert filt.op() != datastore_pb.Query_Filter.IN
	
			prop = filt.property(0).name().decode('utf-8')
			op = operators[filt.op()]
	
			filter_val_list = [datastore_types.FromPropertyPb(filter_prop)
							 for filter_prop in filt.property_list()]
	
			def passes_filter(entity):
				"""Returns True if the entity passes the filter, False otherwise.
		
				The filter being evaluated is filt, the current filter that we're on
				in the list of filters in the query.
				"""
				log.debug('filter check for entity: %r' %entity)
				if not has_prop_indexed(entity, prop):
					return False
		
				try:
					entity_vals = datastore._GetPropertyValue(entity, prop)
				except KeyError:
					entity_vals = []
		
				if not isinstance(entity_vals, list):
					entity_vals = [entity_vals]
		
				for fixed_entity_val in entity_vals:
					for filter_val in filter_val_list:
						fixed_entity_type = self._PROPERTY_TYPE_TAGS.get(
																		fixed_entity_val.__class__)
						filter_type = self._PROPERTY_TYPE_TAGS.get(filter_val.__class__)
						if fixed_entity_type == filter_type:
							comp = u'%r %s %r' % (fixed_entity_val, op, filter_val)
						elif op != '==':
							comp = '%r %s %r' % (fixed_entity_type, op, filter_type)
						else:
							continue
		
						logging.log(logging.DEBUG - 1,
								'Evaling filter expression "%s"', comp)
		
						try:
							ret = eval(comp)
							if ret and ret != NotImplementedError:
								return True
						except TypeError:
							pass
		
				return False
	
			results = filter(passes_filter, results)
		log.debug('entity list after filter operation: %r' %results)
	
		for order in orders:
			prop = order.property().decode('utf-8')
			results = [entity for entity in results if has_prop_indexed(entity, prop)]
	
		def order_compare_entities(a, b):
			""" Return a negative, zero or positive number depending on whether
			entity a is considered smaller than, equal to, or larger than b,
			according to the query's orderings. """
			cmped = 0
			for o in orders:
				prop = o.property().decode('utf-8')
		
				reverse = (o.direction() is datastore_pb.Query_Order.DESCENDING)
		
				a_val = datastore._GetPropertyValue(a, prop)
				if isinstance(a_val, list):
					a_val = sorted(a_val, order_compare_properties, reverse=reverse)[0]
		
				b_val = datastore._GetPropertyValue(b, prop)
				if isinstance(b_val, list):
					b_val = sorted(b_val, order_compare_properties, reverse=reverse)[0]
		
				cmped = order_compare_properties(a_val, b_val)
		
				if o.direction() is datastore_pb.Query_Order.DESCENDING:
					cmped = -cmped
	
				if cmped != 0:
					return cmped
	
			if cmped == 0:
				return cmp(a.key(), b.key())
	
		def order_compare_properties(x, y):
			"""Return a negative, zero or positive number depending on whether
			property value x is considered smaller than, equal to, or larger than
			property value y. If x and y are different types, they're compared based
			on the type ordering used in the real datastore, which is based on the
			tag numbers in the PropertyValue PB.
			"""
			if isinstance(x, datetime.datetime):
				x = datastore_types.DatetimeToTimestamp(x)
			if isinstance(y, datetime.datetime):
				y = datastore_types.DatetimeToTimestamp(y)
	
			x_type = self._PROPERTY_TYPE_TAGS.get(x.__class__)
			y_type = self._PROPERTY_TYPE_TAGS.get(y.__class__)
	
			if x_type == y_type:
				try:
					return cmp(x, y)
				except TypeError:
					return 0
			else:
				return cmp(x_type, y_type)
	
		results.sort(order_compare_entities)

		cursor = _Cursor(query, results, order_compare_entities)
		self.__queries[cursor.cursor] = cursor
	
		if query.has_count():
			count = query.count()
		elif query.has_limit():
			count = query.limit()
		else:
			count = _BATCH_SIZE
	
		cursor.PopulateQueryResult(query_result, count,
									 query.offset(), compile=query.compile())
	
		if query.compile():
			compiled_query = query_result.mutable_compiled_query()
			compiled_query.set_keys_only(query.keys_only())
			compiled_query.mutable_primaryscan().set_index_name(query.Encode())
	
	def _Dynamic_Next(self, next_request, query_result):
		self.__ValidateAppId(next_request.cursor().app())
	
		cursor_handle = next_request.cursor().cursor()
	
		try:
			cursor = self.__queries[cursor_handle]
		except KeyError:
			raise apiproxy_errors.ApplicationError(
				datastore_pb.Error.BAD_REQUEST, 'Cursor %d not found' % cursor_handle)
	
		assert cursor.app == next_request.cursor().app()
	
		count = _BATCH_SIZE
		if next_request.has_count():
			count = next_request.count()
		cursor.PopulateQueryResult(query_result,
									 count, next_request.offset(),
									 next_request.compile())
	
	def _Dynamic_Count(self, query, integer64proto):
		query_result = datastore_pb.QueryResult()
		self._Dynamic_RunQuery(query, query_result)
		cursor = query_result.cursor().cursor()
		integer64proto.set_value(min(self.__queries[cursor].count, _MAXIMUM_RESULTS))
		del self.__queries[cursor]
