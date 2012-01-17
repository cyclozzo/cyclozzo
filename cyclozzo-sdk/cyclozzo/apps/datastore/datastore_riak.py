#! /usr/bin/env python
#
# Datastore implementation for Riak.
#    It should be registered by 
#        apiproxy_stub_map.apiproxy.RegisterStub('datastore', DatastoreStub())
#
# @author: Sreejith K
# Created on 27th March 2010

import logging
import threading
import datetime
import dateutil
import re
import array
import itertools
import uuid
import types

import riak

from cyclozzo.sdk import app
from cyclozzo.apps.api import apiproxy_stub
from cyclozzo.apps.api import datastore, datastore_types, datastore_errors, users
from cyclozzo.apps.datastore import datastore_pb, entity_pb
from cyclozzo.apps.datastore import sortable_pb_encoder
from cyclozzo.apps.datastore import datastore_index
from cyclozzo.apps.datastore import datastore_stub_util
from cyclozzo.apps.api import namespace_manager

import __builtin__
buffer = __builtin__.buffer

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


class RiakStub(apiproxy_stub.APIProxyStub):

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


    def __init__(self, app_id,
                host='127.0.0.1',
                port=8091,
                service_name='datastore_v3',
                trusted=False):
        """
        Initialize this stub with the service name.
        """
        self.__app_id = app_id
        self.__host = host
        self.__port = port
        self.__trusted = trusted
        self.__queries = {}
        
        self.__id_lock = threading.Lock()
        self.__id_map = {}
        
        # transaction support
        self.__next_tx_handle = 1
        self.__tx_writes = {}
        self.__tx_deletes = set()
        self.__tx_actions = []
        self.__tx_lock = threading.Lock()

        super(RiakStub, self).__init__(service_name)

    def Clear(self):
        """Clears the datastore.
        
        This is mainly for testing purposes and the admin console.
        """
        self.__queries = {}
        self.__query_history = {}
        self.__indexes = {}
        self.__id_map = {}
        self.__next_tx_handle = 1
        self.__tx_writes = {}
        self.__tx_deletes = set()
        self.__tx_actions = []

    def _GetRiakClient(self):
        """Get a new Riak connection"""
        return riak.RiakClient(self.__host, self.__port)
        
    def _AppIdNamespaceKindForKey(self, key):
        """ Get (app, kind) tuple from given key.
    
        The (app, kind) tuple is used as an index into several internal
        dictionaries, e.g. __entities.
    
        Args:
            key: entity_pb.Reference
    
        Returns:
            Tuple (app, kind), both are unicode strings.
        """
        last_path = key.path().element_list()[-1]
        return (datastore_types.EncodeAppIdNamespace(key.app(), key.name_space()),
                last_path.type())

    @staticmethod
    def __EncodeIndexPB(pb):
        if isinstance(pb, entity_pb.PropertyValue) and pb.has_uservalue():
            userval = entity_pb.PropertyValue()
            userval.mutable_uservalue().set_email(pb.uservalue().email())
            userval.mutable_uservalue().set_auth_domain(pb.uservalue().auth_domain())
            userval.mutable_uservalue().set_gaiaid(0)
            pb = userval
        encoder = sortable_pb_encoder.Encoder()
        pb.Output(encoder)
        return buffer(encoder.buffer().tostring())

    @staticmethod
    def __GetEntityKind(key):
        if isinstance(key, entity_pb.EntityProto):
            key = key.key()
        return key.path().element_list()[-1].type()

    def __ValidateAppId(self, app_id):
        """Verify that this is the stub for app_id.
    
        Args:
            app_id: An application ID.
    
        Raises:
            datastore_errors.BadRequestError: if this is not the stub for app_id.
        """
        assert app_id
        if not self.__trusted and app_id != self.__app_id:
            raise datastore_errors.BadRequestError(
                    'app %s cannot access app %s\'s data' % (self.__app_id, app_id))

    def __ValidateKey(self, key):
        """Validate this key.

        Args:
            key: entity_pb.Reference

        Raises:
            datastore_errors.BadRequestError: if the key is invalid
        """
        assert isinstance(key, entity_pb.Reference)

        self.__ValidateAppId(key.app())

        for elem in key.path().element_list():
            if elem.has_id() == elem.has_name():
                raise datastore_errors.BadRequestError(
                    'each key path element should have id or name but not both: %r'
                    % key)

    def __id_for_key(self, key):
        db_path = []
        def add_element_to_db_path(elem):
            db_path.append(elem.type())
            if elem.has_name():
                db_path.append(elem.name())
            else:
                db_path.append("\t" + str(elem.id()).zfill(10))
        for elem in key.path().element_list():
            add_element_to_db_path(elem)
        return "\10".join(db_path)
    
    def __key_for_id(self, id):
        def from_db(value):
            if value.startswith("\t"):
                return int(value[1:])
            return value
        return datastore_types.Key.from_path(*[from_db(a) for a in id.split("\10")])

    def __create_riak_value_for_value(self, value, binary_bucket, pointer):
        if isinstance(value, datetime.datetime):
            return {
                    'class': 'datetime',
                    'value': value.isoformat()
                    }
        if isinstance(value, datastore_types.Rating):
            return {
                    'class': 'rating',
                    'rating': int(value),
                    }
        if isinstance(value, datastore_types.Category):
            return {
                    'class': 'category',
                    'category': str(value),
                    }
        if isinstance(value, datastore_types.Key):
            return {
                    'class': 'key',
                    'path': self.__id_for_key(value._ToPb()),
                    }
        if isinstance(value, types.ListType):
            list_for_db = [self.__create_riak_value_for_value(v, binary_bucket, pointer) for v in value]
            sorted_list = sorted(value)
            return {
                    'class': 'list',
                    'list': list_for_db,
                    'ascending_sort_key': self.__create_riak_value_for_value(
                                        sorted_list[0], binary_bucket, pointer),
                    'descending_sort_key': self.__create_riak_value_for_value(
                                        sorted_list[-1], binary_bucket, pointer),
                    }
        if isinstance(value, users.User):
            return {
                    'class': 'user',
                    'email': value.email(),
                    }
        if isinstance(value, datastore_types.Text):
            return {
                    'class': 'text',
                    'string': unicode(value),
                    }
        if isinstance(value, datastore_types.Blob):
            # we store binary data in a different bucket
            blob = binary_bucket.new_binary(pointer, value)
            blob.store()
            return {
                    'class': 'blob',
                    'key': pointer
                    }
        if isinstance(value, datastore_types.ByteString):
            # we store binary data in a different bucket
            byte_string = binary_bucket.new_binary(pointer, value)
            byte_string.store()
            return {
                    'class': 'bytes',
                    'key': pointer
                    }
        if isinstance(value, datastore_types.IM):
            return {
                    'class': 'im',
                    'protocol': value.protocol,
                    'address': value.address,
                    }
        if isinstance(value, datastore_types.GeoPt):
            return {
                    'class': 'geopt',
                    'lat': value.lat,
                    'lon': value.lon,
                    }
        if isinstance(value, datastore_types.Email):
            return {
                    'class': 'email',
                    'value': value,
                    }
        if isinstance(value, datastore_types.BlobKey):
            return {
                    'class': 'blobkey',
                    'value': str(value),
                    }
        return value
    
    def __create_value_for_riak_value(self, riak_value, binary_bucket):
        if isinstance(riak_value, types.DictType):
            if riak_value['class'] == 'datetime':
                return dateutil.parser.parse(riak_value['value'])
            if riak_value['class'] == 'rating':
                return datastore_types.Rating(int(riak_value["rating"]))
            if riak_value['class'] == 'category':
                return datastore_types.Category(riak_value["category"])
            if riak_value['class'] == 'key':
                return self.__key_for_id(riak_value['path'])
            if riak_value['class'] == 'list':
                return [self.__create_value_for_riak_value(v, binary_bucket)
                            for v in riak_value['list']]
            if riak_value['class'] == 'user':
                return users.User(email=riak_value["email"])
            if riak_value['class'] == 'text':
                return datastore_types.Text(riak_value['string'])
            if riak_value['class'] == 'im':
                return datastore_types.IM(riak_value['protocol'],
                                          riak_value['address'])
            if riak_value['class'] == 'geopt':
                return datastore_types.GeoPt(riak_value['lat'], riak_value['lon'])
            if riak_value['class'] == 'email':
                return datastore_types.Email(riak_value['value'])
            if riak_value['class'] == 'blob':
                blob = binary_bucket.get_binary(riak_value['key']).get_data()
                return datastore_types.Blob(blob)
            if riak_value['class'] == 'bytes':
                byte_string = binary_bucket.get_binary(riak_value['key']).get_data()
                return datastore_types.ByteString(byte_string)
            if riak_value['class'] == 'blobkey':
                return datastore_types.BlobKey(riak_value['value'])
        return riak_value

    def __AllocateIds(self, kind, size=None, max=None):
        """Allocates IDs.

        Args:
            kind: A kind.
            size: Number of IDs to allocate.
            max: Upper bound of IDs to allocate.

        Returns:
            Integer as the beginning of a range of size IDs.
        """
        client = self._GetRiakClient()
        self.__id_lock.acquire()
        ret = None
        _id = 'IdSeq_%s' % kind
        
        id_bucket = client.bucket('%s_%s_%s' % (self.__app_id, '', 'datastore'))
        
        current_next_id = id_bucket.get(_id).get_data()

        if not current_next_id:
            id_bucket.new(_id, 1).store()
            current_next_id = 1
        if size is not None:
            assert size > 0
            next_id, block_size = self.__id_map.get(kind, (0, 0))
            if not block_size:
                block_size = (size / 1000 + 1) * 1000
                incr = next_id + block_size
                id_bucket.new(_id, current_next_id+incr).store()
                next_id = current_next_id + incr
                current_next_id += incr
            if size > block_size:
                incr = size
                id_bucket.new(_id, current_next_id+incr).store()
                ret = current_next_id + incr
                current_next_id += incr
            else:
                ret = next_id;
                next_id += size
                block_size -= size
                self.__id_map[kind] = (next_id, block_size)
        else:
            next_id_from_cell = int(id_bucket.get(_id).get_data())
            if max and max >= next_id_from_cell:
                id_bucket.new(_id, max+1).store()
        
        self.__id_lock.release()
        return ret
    
    def __PutEntities(self, entities):
        """Inserts or updates entities in the DB.
        
        Args:
            entities: A list of entities to store.
        """
        client = self._GetRiakClient()
        for entity in entities:
            # recreate entity from protocol buffer
            entity = datastore.Entity._FromPb(entity)
            entity_bucket_name = '%s_%s_%s' % (entity.app(), entity.namespace(), entity.kind())
            entity_bucket = client.bucket(entity_bucket_name)
            # we store binary properties in a different bucket as binary data
            binary_bucket_name = entity_bucket_name + ':BINARY'
            binary_bucket = client.bucket(binary_bucket_name)
            
            data = {}
            for (k, v) in entity.iteritems():
                v = self.__create_riak_value_for_value(v, binary_bucket, str(entity.key().id_or_name()) + ':' + k)
                data[k] = v
            
            riak_entity = entity_bucket.new(str(entity.key().id_or_name()), data)
            riak_entity.set_usermeta( { 'key' : str(entity.key()) } )
            riak_entity.store()
        
    def __DeleteEntities(self, keys):
        """Deletes entities from the DB.
        
        Args:
            keys: A list of keys to delete index entries for.
        Returns:
            The number of rows deleted.
        """
        client = self._GetRiakClient()
        keys = [datastore_types.Key._FromPb(key) for key in keys]
        for key in keys:
            kind, namespace = key.kind(), key.namespace()
            log.debug('deleting cells with key: %s' %key.id_or_name())
            entity_bucket_name = '%s_%s_%s' % (self.__app_id, namespace, kind)
            entity_bucket = client.bucket(entity_bucket_name)
            binary_bucket_name = entity_bucket_name + ':BINARY'
            binary_bucket = client.bucket(binary_bucket_name)
            entity = entity_bucket.get(key.id_or_name())
            if isinstance(entity, types.DictType):
                if entity['class'] == 'blob' or entity['class'] == 'bytes':
                    binary_key = entity['key']
                    binary_bucket.get(binary_key).delete()
            entity.delete()

    def _Dynamic_Put(self, put_request, put_response):
        entities = put_request.entity_list()
        for entity in entities:
            self.__ValidateKey(entity.key())
            
            for prop in itertools.chain(entity.property_list(),
                                    entity.raw_property_list()):
                datastore_stub_util.FillUser(prop)

            assert entity.has_key()
            assert entity.key().path().element_size() > 0
            
            last_path = entity.key().path().element_list()[-1]
            if last_path.id() == 0 and not last_path.has_name():
                id_ = self.__AllocateIds(last_path.type(), 1)
                last_path.set_id(id_)
                
                assert entity.entity_group().element_size() == 0
                group = entity.mutable_entity_group()
                root = entity.key().path().element(0)
                group.add_element().CopyFrom(root)
            else:
                assert (entity.has_entity_group() and
                    entity.entity_group().element_size() > 0)
                
            if put_request.transaction().handle():
                self.__tx_writes[entity.key()] = entity
                self.__tx_deletes.discard(entity.key())
        
        if not put_request.transaction().handle():
            self.__PutEntities(entities)
            
        put_response.key_list().extend([e.key() for e in entities])

    def _Dynamic_Delete(self, delete_request, delete_response):
        keys = delete_request.key_list()
        for key in keys:
            self.__ValidateAppId(key.app())
            if delete_request.transaction().handle():
                self.__tx_deletes.add(key)
                self.__tx_writes.pop(key, None)
        
        if not delete_request.transaction().handle():
            self.__DeleteEntities(delete_request.key_list())

    def _Dynamic_Drop(self, drop_request, drop_response):
        client = self._GetRiakClient()
        kind = drop_request.kind
        namespace = namespace_manager.get_namespace()
    
    def _Dynamic_Get(self, get_request, get_response):
        client = self._GetRiakClient()
        for key in get_request.key_list():
            appid_namespace, kind = self._AppIdNamespaceKindForKey(key)
            namespace = appid_namespace.rsplit('!', 1)[1] if '!' in appid_namespace else ''

            total_cells = []
            key_pb = key
            key = datastore_types.Key._FromPb(key)
            
            entity_bucket_name = '%s_%s_%s' % (self.__app_id, namespace, kind)
            entity_bucket = client.bucket(entity_bucket_name)
            # binary values are searched in this bucket
            binary_bucket_name = entity_bucket_name + ':BINARY'
            binary_bucket = client.bucket(binary_bucket_name)
            riak_entity = entity_bucket.get(key.id_or_name()).get_data()

            group = get_response.add_entity()

            entity = datastore.Entity(kind=kind, parent=key.parent(), name=key.name(), id=key.id())
            
            for property_name, property_value in riak_entity.iteritems():
                property_value = self.__create_value_for_riak_value(riak_entity[property_name], binary_bucket)
                entity[property_name] = property_value
            
            pb = entity._ToPb()
            #if not key.name():
            #   pb.key().path().element_list()[-1].set_id(key.id())
            
            group.mutable_entity().CopyFrom(pb)

    def _Dynamic_RunQuery(self, query, query_result):
        client = self._GetRiakClient()
        kind = query.kind()
        keys_only = query.keys_only()
        filters = query.filter_list()
        orders = query.order_list()
        offset = query.offset()
        limit = query.limit()
        namespace = query.name_space()
        logging.debug('offset: %d limit: %d' %(offset, limit))
        
        if filters or orders:
            row_limit = 0
        else:
            row_limit = offset + limit
        
        entity_bucket_name = '%s_%s_%s' % (self.__app_id, namespace, kind)
        entity_bucket = client.bucket(entity_bucket_name)
        binary_bucket_name = entity_bucket_name + ':BINARY'
        binary_bucket = client.bucket(binary_bucket_name)

        riak_query = client.add(entity_bucket_name)
        
        operators = {datastore_pb.Query_Filter.LESS_THAN:             '<',
                     datastore_pb.Query_Filter.LESS_THAN_OR_EQUAL:    '<=',
                     datastore_pb.Query_Filter.GREATER_THAN:            '>',
                     datastore_pb.Query_Filter.GREATER_THAN_OR_EQUAL: '>=',
                     datastore_pb.Query_Filter.EQUAL:                 '==',
                     }
        
        condition_list = []
        for filt in filters:
            assert filt.op() != datastore_pb.Query_Filter.IN
            prop = filt.property(0).name().decode('utf-8')
            op = operators[filt.op()]
            filter_val_list = [datastore_types.FromPropertyPb(filter_prop)
                             for filter_prop in filt.property_list()]
            if len(filter_val_list) == 1:
                # not a list, take the first element
                filter_val = filter_val_list[0]
            else:
                # filter on a list
                filter_val = filter_val_list
            condition = 'data.%s %s %r' % (prop, op, str(filter_val))
            condition_list.append(condition)

        if not condition_list:
            filter_condition = 'true'
        else:
            filter_condition = ' && '.join(condition_list).strip()
        filter_condition = 'if (%s)' % filter_condition
        
        # add a map phase to filter out entities
        map_func = 'function(v) { ' \
                        + 'var data = JSON.parse(v.values[0].data); ' \
                        + filter_condition + ' ' \
                        + '{ return [[v.values[0].metadata, data]]; } ' \
                        + 'return []; }'
        logging.debug('map function: %s' % map_func)
        riak_query.map(map_func)
        
        for order in orders:
            prop = order.property().decode('utf-8')
            if order.direction() is datastore_pb.Query_Order.DESCENDING:
                reduce_func = 'function(a, b) { return b.%s - a.%s }' % (prop, prop)
            else:
                reduce_func = 'function(a, b) { return a.%s - b.%s }' % (prop, prop)
            logging.debug('reduce function: %s' % reduce_func)
            # add a reduce phase to sort the entities based on property direction
            riak_query.reduce('Riak.reduceSort', {'arg': reduce_func})

        if limit:
            # reduce phase for applying limit
            start = offset
            end = offset + limit
            logging.debug('reduce function: Riak.reduceSlice(start: %d, end:%d)' %(start, end))
            riak_query.reduce('Riak.reduceSlice', {'arg': [start, end]})

        results = []
        for result in riak_query.run():
            metadata, riak_entity = result
            key = metadata['X-Riak-Meta']['X-Riak-Meta-Key']
            key = datastore_types.Key(encoded=key)
            entity = datastore.Entity(kind=kind, parent=key.parent(), name=key.name(), id=key.id())
            for property_name, property_value in riak_entity.iteritems():
                property_value = self.__create_value_for_riak_value(riak_entity[property_name], binary_bucket)
                entity[property_name] = property_value
            results.append(entity)

        query.set_app(self.__app_id)
        datastore_types.SetNamespace(query, namespace)
        encoded = datastore_types.EncodeAppIdNamespace(self.__app_id, namespace)
    
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

    def __ValidateTransaction(self, tx):
        """Verify that this transaction exists and is valid.
        
        Args:
            tx: datastore_pb.Transaction
        
        Raises:
            datastore_errors.BadRequestError: if the tx is valid or doesn't exist.
        """
        assert isinstance(tx, datastore_pb.Transaction)
        self.__ValidateAppId(tx.app())

    def _Dynamic_BeginTransaction(self, request, transaction):
        self.__ValidateAppId(request.app())
        
        self.__tx_lock.acquire()
        handle = self.__next_tx_handle
        self.__next_tx_handle += 1
        
        transaction.set_app(request.app())
        transaction.set_handle(handle)
        
        self.__tx_actions = []
    
    def _Dynamic_AddActions(self, request, _):
        """Associates the creation of one or more tasks with a transaction.
        
        Args:
            request: A taskqueue_service_pb.TaskQueueBulkAddRequest containing the
                tasks that should be created when the transaction is comitted.
        """
        if ((len(self.__tx_actions) + request.add_request_size()) >
                _MAX_ACTIONS_PER_TXN):
            raise apiproxy_errors.ApplicationError(
                            datastore_pb.Error.BAD_REQUEST,
                            'Too many messages, maximum allowed %s' % _MAX_ACTIONS_PER_TXN)
        
        new_actions = []
        for add_request in request.add_request_list():
            self.__ValidateTransaction(add_request.transaction())
            clone = taskqueue_service_pb.TaskQueueAddRequest()
            clone.CopyFrom(add_request)
            clone.clear_transaction()
            new_actions.append(clone)
        
        self.__tx_actions.extend(new_actions)
        
    def _Dynamic_Commit(self, transaction, transaction_response):
        self.__ValidateTransaction(transaction)
        
        try:
            self.__PutEntities(self.__tx_writes.values())
            self.__DeleteEntities(self.__tx_deletes)
            for action in self.__tx_actions:
                try:
                  apiproxy_stub_map.MakeSyncCall(
                      'taskqueue', 'Add', action, api_base_pb.VoidProto())
                except apiproxy_errors.ApplicationError, e:
                     logging.warning('Transactional task %s has been dropped, %s',
                              action, e)
                     pass
        finally:
            self.__tx_writes = {}
            self.__tx_deletes = set()
            self.__tx_actions = []
            self.__tx_lock.release()
            
    def _Dynamic_Rollback(self, transaction, transaction_response):
        self.__ValidateTransaction(transaction)
        
        self.__tx_writes = {}
        self.__tx_deletes = set()
        self.__tx_actions = []
        self.__tx_lock.release()