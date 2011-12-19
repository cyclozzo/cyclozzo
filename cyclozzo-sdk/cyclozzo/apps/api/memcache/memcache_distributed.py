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

"""non-stub version of the memcache API, keeping all data in memcached."""

# Programmer: Chris Bunch
# uses the python-memcached library to interface with memcached
# tested with python-memcached 1.40, from apt-get

import memcache
import time
import os

from cyclozzo.apps.api import apiproxy_stub
from cyclozzo.apps.api.memcache import memcache_service_pb

MemcacheSetResponse = memcache_service_pb.MemcacheSetResponse
MemcacheSetRequest = memcache_service_pb.MemcacheSetRequest
MemcacheIncrementRequest = memcache_service_pb.MemcacheIncrementRequest
MemcacheDeleteResponse = memcache_service_pb.MemcacheDeleteResponse

class CacheEntry(object):
  """An entry in the cache."""

  def __init__(self, value, expiration, flags, gettime):
    """Initializer.

    Args:
      value: String containing the data for this entry.
      expiration: Number containing the expiration time or offset in seconds
        for this entry.
      flags: Opaque flags used by the memcache implementation.
      gettime: Used for testing. Function that works like time.time().
    """
    assert isinstance(value, basestring)
    assert isinstance(expiration, (int, long))

    self._gettime = gettime
    self.value = value
    self.flags = flags
    self.created_time = self._gettime()
    self.will_expire = expiration != 0
    self.locked = False
    self._SetExpiration(expiration)

  def _SetExpiration(self, expiration):
    """Sets the expiration for this entry.

    Args:
      expiration: Number containing the expiration time or offset in seconds
        for this entry. If expiration is above one month, then it's considered
        an absolute time since the UNIX epoch.
    """
    if expiration > (86400 * 30):
      self.expiration_time = expiration
    else:
      self.expiration_time = self._gettime() + expiration

  def CheckExpired(self):
    """Returns True if this entry has expired; False otherwise."""
    return self.will_expire and self._gettime() >= self.expiration_time

  def ExpireAndLock(self, timeout):
    """Marks this entry as deleted and locks it for the expiration time.

    Used to implement memcache's delete timeout behavior.

    Args:
      timeout: Parameter originally passed to memcache.delete or
        memcache.delete_multi to control deletion timeout.
    """
    self.will_expire = True
    self.locked = True
    self._SetExpiration(timeout)

  def CheckLocked(self):
    """Returns True if this entry was deleted but has not yet timed out."""
    return self.locked and not self.CheckExpired()


class MemcacheService(apiproxy_stub.APIProxyStub):
  """Python only memcache service.

  This service keeps all data in any external servers running memcached.
  """

  def __init__(self, servers, gettime=time.time, service_name='memcache'):
    """Initializer.

    Args:
      gettime: time.time()-like function used for testing.
      service_name: Service name expected for all calls.
    """
    super(MemcacheService, self).__init__(service_name)
    self._gettime = gettime

    memcaches = [ip + ":11211" for ip in servers if ip != '']

    self._memcache = memcache.Client(memcaches, debug=0)
    self._ResetStats()

    self._the_cache = {}

  def _ResetStats(self):
    """Resets statistics information."""
    self._hits = 0
    self._misses = 0
    self._byte_hits = 0
    self._cache_creation_time = self._gettime()

  def _GetKey(self, namespace, key):
    """Retrieves a CacheEntry from the cache if it hasn't expired.

    Does not take deletion timeout into account.

    Args:
      namespace: The namespace that keys are stored under.
      key: The key to retrieve from the cache.

    Returns:
      The corresponding CacheEntry instance, or None if it was not found or
      has already expired.
    """
    appname = os.environ['APPLICATION_ID']
    internal_key = "__" + appname + "__" + namespace + "__" + key

    entry = self._memcache.get(internal_key)
    if entry is None:
      return None
    else:
      return entry

  def _Dynamic_Get(self, request, response):
    """Implementation of MemcacheService::Get().

    Args:
      request: A MemcacheGetRequest.
      response: A MemcacheGetResponse.
    """
    namespace = request.name_space()
    keys = set(request.key_list())
    for key in keys:
      value = self._GetKey(namespace, key)
      if value is None: 
        continue
      item = response.add_item()
      item.set_key(key)
      item.set_value(value)

  def _Dynamic_Set(self, request, response):
    """Implementation of MemcacheService::Set().

    Args:
      request: A MemcacheSetRequest.
      response: A MemcacheSetResponse.
    """
    namespace = request.name_space()
    for item in request.item_list():
      key = item.key()
      set_policy = item.set_policy()
      old_entry = self._GetKey(namespace, key)

      set_status = MemcacheSetResponse.NOT_STORED
      if ((set_policy == MemcacheSetRequest.SET) or
          (set_policy == MemcacheSetRequest.ADD and old_entry is None) or
          (set_policy == MemcacheSetRequest.REPLACE and old_entry is not None)):

        if (old_entry is None or
            set_policy == MemcacheSetRequest.SET
            or not old_entry.CheckLocked()):
          appname = os.environ['APPLICATION_ID']
          internal_key = "__" + appname + "__" + namespace + "__" + key

          if self._memcache.set(internal_key, item.value(), item.expiration_time()):
            set_status = MemcacheSetResponse.STORED

      response.add_set_status(set_status)

  def _Dynamic_Delete(self, request, response):
    """Implementation of MemcacheService::Delete().

    Args:
      request: A MemcacheDeleteRequest.
      response: A MemcacheDeleteResponse.
    """
    namespace = request.name_space()
    for item in request.item_list():
      key = item.key()
      entry = self._GetKey(namespace, key)

      delete_status = MemcacheDeleteResponse.DELETED
      if entry is None:
        delete_status = MemcacheDeleteResponse.NOT_FOUND
      else:
        appname = os.environ['APPLICATION_ID']
        internal_key = "__" + appname + "__" + namespace + "__" + key
        self._memcache.delete(internal_key)

      response.add_delete_status(delete_status)

  def _Dynamic_Increment(self, request, response):
    """Implementation of MemcacheService::Increment().

    Args:
      request: A MemcacheIncrementRequest.
      response: A MemcacheIncrementResponse.
    """
    namespace = request.name_space()
    key = request.key()
    delta = request.delta()

    new_value = 0
    try:
      appname = os.environ['APPLICATION_ID']
      internal_key = "__" + appname + "__" + namespace + "__" + key

      if request.direction() == MemcacheIncrementRequest.INCREMENT:
        new_value = self._memcache.incr(internal_key, delta)
      elif request.direction() == MemcacheIncrementRequest.DECREMENT:
        new_value = self._memcache.decr(internal_key, delta)
      else:
        raise ValueError
    except ValueError:
      return

    response.set_new_value(new_value)

  def _Dynamic_FlushAll(self, request, response):
    """Implementation of MemcacheService::FlushAll().

    Args:
      request: A MemcacheFlushRequest.
      response: A MemcacheFlushResponse.
    """
    self._memcache.flush_all()

  def _Dynamic_Stats(self, request, response):
    """Implementation of MemcacheService::Stats().

    CGB: Distributed version has two discrepancies with memcache:

    1) total_items should return the total number of items currently
       in memcache, but memcache's total items stat returns the total items
       that have ever been in memcache. We have resolved to just return zero
       until we implement a better solution for this.

    2) time of oldest item in cache returns the age of the cache, not the
       time of the oldest item. Resolved to just return zero for now.

    Args:
      request: A MemcacheStatsRequest.
      response: A MemcacheStatsResponse.
    """
    mc_stats = self._memcache.get_stats()
    hits = 0
    misses = 0
    bytes_written = 0
    total_items = 0
    bytes = 0
    oldest_item_age = 0

    for mc in mc_stats:
      memcache_stats = mc[1]
      hits += int(memcache_stats['get_hits'])
      misses += int(memcache_stats['get_misses'])
      bytes_written += int(memcache_stats['bytes_written'])
      bytes += int(memcache_stats['bytes'])

    stats = response.mutable_stats()
    stats.set_hits(hits)
    stats.set_misses(misses)
    stats.set_byte_hits(bytes_written)
    stats.set_items(total_items)
    stats.set_bytes(bytes)
    stats.set_oldest_item_age(oldest_item_age)
