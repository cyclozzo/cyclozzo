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
import time
from subprocess import *
import logging, os

def run_command(command, no_wait = False, log = logging.getLogger(__name__), **kwargs):
	try:
		child = Popen(command, **kwargs)
		if not no_wait:
			child.wait()
			out = ''
			if 'stdout' in kwargs:
				out += ''.join(child.stdout.readlines())
			if 'stderr' in kwargs:
				err = ''.join(child.stderr.readlines())
				if len(err) > 0:
					out += err
			return (child.returncode, out)
		else:
			return child
	except Exception, ex:
		log.fatal('run_command failed: %s ' % ex)
		return 128, str(ex)