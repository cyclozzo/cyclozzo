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

"""Task Queue API module."""

from taskqueue import *

import datetime
import os
import time


class _UTCTimeZone(datetime.tzinfo):
	"""UTC timezone."""

	ZERO = datetime.timedelta(0)

	def utcoffset(self, dt):
		return self.ZERO

	def dst(self, dt):
		return self.ZERO

	def tzname(self, dt):
		return 'UTC'

UTC = _UTCTimeZone()


def is_deferred_eta(eta):
	"""Checks whether the given eta is in the future."""

	if hasattr(time, 'tzset'):
		os.environ['TZ'] = 'UTC'
		time.tzset()

	eta = datetime.datetime.fromtimestamp(eta, UTC)
	now = datetime.datetime.now()

	if now.tzinfo is None:
		now = now.replace(tzinfo=UTC)

	if eta > now:
		return True

	return False


def get_new_eta_usec(try_count, backoff_seconds=[5.0]):
	"""Returns new estimated execution time depending on try count.

	Args:
		try_count: current number of retries.
		backoff_seconds: list of float values to configure the backoff behavior.
	"""

	assert len(backoff_seconds) >= 1

	try:
		sec = backoff_seconds[try_count-1]
	except IndexError:
		sec = backoff_seconds[-1]

	eta = datetime.datetime.utcnow() + datetime.timedelta(seconds=sec)

	return int(time.mktime(eta.replace(tzinfo=UTC).timetuple()))
