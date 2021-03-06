# -*- coding: utf-8 -*-
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
"""Memcache integration."""

import base64
import cPickle
import cyclozzo.apps.api.apiproxy_stub
import cyclozzo.apps.api.memcache.memcache_service_pb
import cyclozzo.apps.runtime.apiproxy_errors
import logging
import os
import pylibmc
import time

DEFAULT_ADDR = '127.0.0.1'
DEFAULT_PORT = 11211

MemcacheSetResponse       = (cyclozzo.apps.api.memcache.memcache_service_pb.
                             MemcacheSetResponse)
MemcacheSetRequest        = (cyclozzo.apps.api.memcache.memcache_service_pb.
                             MemcacheSetRequest)
MemcacheIncrementRequest  = (cyclozzo.apps.api.memcache.memcache_service_pb.
                             MemcacheIncrementRequest)
MemcacheIncrementResponse = (cyclozzo.apps.api.memcache.memcache_service_pb.
                             MemcacheIncrementResponse)
MemcacheDeleteResponse    = (cyclozzo.apps.api.memcache.memcache_service_pb.
                             MemcacheDeleteResponse)


def getKey(key, namespace=None):
    """Returns a key."""

    app_id = os.environ.get('APPLICATION_ID', '')
    if app_id: app_id += '.'

    if namespace:
        key = '%(namespace)s.%(key)s' % locals()
    key = '%(app_id)s%(key)s' % locals()
    return base64.b64encode(key)


class MemcacheServiceStub(cyclozzo.apps.api.apiproxy_stub.APIProxyStub):
    """Memcache service stub.

    This stub uses memcached to store data.
    """

    def __init__(self, server, port, service_name='memcache'):
        """Initializes memcache service stub.

        Args:
            config: Dictionary containing configuration parameters.
            service_name: Service name expected for all calls.
        """
        super(MemcacheServiceStub, self).__init__(service_name)
        if not server:
            server = DEFAULT_ADDR
        if not port:
            port = DEFAULT_PORT

        self._cache = pylibmc.Client(['%s:%i' % (server, port)])

    def _GetMemcacheBehavior(self):
        behaviors = self._cache.behaviors
        keys = sorted(k for k in behaviors if not k.startswith('_'))
        sorted_behaviors = [(k, behaviors[k]) for k in keys]
        logging.debug("Memcache behavior: %s" % sorted_behaviors)
        return sorted_behaviors

    def _Dynamic_Get(self, request, response):
        """Implementation of MemcacheService::Get().

        Args:
            request: A MemcacheGetRequest.
            response: A MemcacheGetResponse.
        """
        for key in set(request.key_list()):
            value = self._cache.get(getKey(key, request.name_space()))
            if value is None:
                continue
            flags = 0
            stored_flags, stored_value = cPickle.loads(value)
            flags |= stored_flags
            item = response.add_item()
            item.set_key(key)
            item.set_value(stored_value)
            item.set_flags(flags)

    def _Dynamic_Set(self, request, response):
        """Implementation of MemcacheService::Set().

        Args:
            request: A MemcacheSetRequest.
            response: A MemcacheSetResponse.
        """
        for item in request.item_list():
            key = getKey(item.key(), request.name_space())
            set_policy = item.set_policy()
            old_entry = self._cache.get(key)
            set_status = MemcacheSetResponse.NOT_STORED

            set_value = cPickle.dumps([item.flags(), item.value()])

            if ((set_policy == MemcacheSetRequest.SET) or
                (set_policy == MemcacheSetRequest.ADD and old_entry is None) or
                (set_policy == MemcacheSetRequest.REPLACE and
                 old_entry is not None)):

                if (old_entry is None or set_policy == MemcacheSetRequest.SET):
                    self._cache.set(key, set_value, item.expiration_time())
                    set_status = MemcacheSetResponse.STORED
                elif (set_policy == MemcacheSetRequest.REPLACE):
                    self._cache.replace(key, set_value)

            response.add_set_status(set_status)

    def _Dynamic_Delete(self, request, response):
        """Implementation of MemcacheService::Delete().

        Args:
            request: A MemcacheDeleteRequest.
            response: A MemcacheDeleteResponse.
        """
        for item in request.item_list():
            key = getKey(item.key(), request.name_space())
            entry = self._cache.get(key)
            delete_status = MemcacheDeleteResponse.DELETED

            if entry is None:
                delete_status = MemcacheDeleteResponse.NOT_FOUND
            else:
                self._cache.delete(key)

            response.add_delete_status(delete_status)

    def _Increment(self, namespace, request):
        """Internal function for incrementing from a MemcacheIncrementRequest.

        Args:
            namespace: A string containing the namespace for the request,
                if any. Pass an empty string if there is no namespace.
            request: A MemcacheIncrementRequest instance.

        Returns:
            An integer or long if the offset was successful, None on error.
        """
        if not request.delta():
            return None

        key = getKey(request.key(), namespace)
        value = self._cache.get(key)
        if value is None:
            if not request.has_initial_value():
                return None
            flags, stored_value = (cyclozzo.apps.api.memcache.TYPE_INT,
                                   str(request.initial_value()))
        else:
            flags, stored_value = cPickle.loads(value)

        if flags == cyclozzo.apps.api.memcache.TYPE_INT:
            new_value = int(stored_value)
        elif flags == cyclozzo.apps.api.memcache.TYPE_LONG:
            new_value = long(stored_value)
        if request.direction() == MemcacheIncrementRequest.INCREMENT:
            new_value += request.delta()
        elif request.direction() == MemcacheIncrementRequest.DECREMENT:
            new_value -= request.delta()

        new_stored_value = cPickle.dumps([flags, str(new_value)])
        try:
            self._cache.set(key, new_stored_value)
        except:
            return None

        return new_value

    def _Dynamic_Increment(self, request, response):
        """Implementation of MemcacheService::Increment().

        Args:
            request: A MemcacheIncrementRequest.
            response: A MemcacheIncrementResponse.
        """
        new_value = self._Increment(request.name_space(), request)
        if new_value is None:
            raise cyclozzo.apps.runtime.apiproxy_errors.ApplicationError(
                cyclozzo.apps.api.memcache.memcache_service_pb.
                MemcacheServiceError.UNSPECIFIED_ERROR)
        response.set_new_value(new_value)

    def _Dynamic_BatchIncrement(self, request, response):
        """Implementation of MemcacheService::BatchIncrement().

        Args:
            request: A MemcacheBatchIncrementRequest.
            response: A MemcacheBatchIncrementResponse.
        """
        namespace = request.name_space()
        for request_item in request.item_list():
            new_value = self._Increment(namespace, request_item)
            item = response.add_item()
            if new_value is None:
                item.set_increment_status(MemcacheIncrementResponse.NOT_CHANGED)
            else:
                item.set_increment_status(MemcacheIncrementResponse.OK)
                item.set_new_value(new_value)

    def _Dynamic_FlushAll(self, request, response):
        """Implementation of MemcacheService::FlushAll().

        Args:
            request: A MemcacheFlushRequest.
            response: A MemcacheFlushResponse.
        """

        self._cache.flush_all()

    def _Dynamic_Stats(self, request, response):
        """Implementation of MemcacheService::Stats().

        Args:
            request: A MemcacheStatsRequest.
            response: A MemcacheStatsResponse.
        """
        stats = response.mutable_stats()

        num_servers = 0
        hits_total = 0
        misses_total = 0
        byte_hits_total = 0
        items_total = 0
        bytes_total = 0
        time_total = 0

        def get_stats_value(stats_dict, key, _type=int):
            if key not in stats_dict:
                logging.warn("No stats for key '%s'." % key) 
            return _type(stats_dict.get(key, '0'))

        for server, server_stats in self._cache.get_stats():
            num_servers += 1
            hits_total += get_stats_value(server_stats, 'get_hits')
            misses_total += get_stats_value(server_stats, 'get_misses')
            byte_hits_total += get_stats_value(server_stats, 'bytes_read') 
            items_total += get_stats_value(server_stats, 'curr_items') 
            bytes_total += get_stats_value(server_stats, 'bytes') 
            time_total += get_stats_value(server_stats, 'time', float) 

        stats.set_hits(hits_total)
        stats.set_misses(misses_total)
        stats.set_byte_hits(byte_hits_total)
        stats.set_items(items_total)
        stats.set_bytes(bytes_total)

        stats.set_oldest_item_age(time.time() - time_total / num_servers)
