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
# Cyclozzo SDK shared master
#
import os
import sys
import traceback
import logging
import datetime
import time
import inspect
import ctypes
import mutex
from collections import deque

__shared_log_queue = deque()
__api_stats = {}
__api_disabled = False
__master_mutex = mutex.mutex()
__last_timestamp = 0
__mcycles_per_minute = 0
__seconds_spent = 0

log = logging.getLogger(__name__)

def get_shared_log():
    global __shared_log_queue
    return __shared_log_queue

def append_app_log(log_data, code = 0):
    if log_data: get_shared_log().append( ( int(time.mktime(datetime.datetime.now().timetuple())), code, str(log_data)) )

def is_api_disabled():
    global __api_disabled
    return __api_disabled

def enable_api():
    global __api_disabled
    logging.info('enabling api...')
    __api_disabled = False

def disable_api():
    global __api_disabled
    logging.info('disabling api...')
    __api_disabled = True

def update_api_stats(service, call, request, response):
    pass

def report_app_log(master_addr, master_port, app_key, app_port, server_key, max_report_count = 500):
    """Callback to report application log to master
    """
    pass


def report_api_metrics(master_addr, master_port, app_key, server_key, app_port):
    """Callback to report api metrics information to master
    """
    pass


def monitor_cpu_mcycles(master_addr, master_port, app_key, mcycles_limit, cpu_monitor_interval):
    """Callback to monitor application's cpu-usage
    """
    pass
