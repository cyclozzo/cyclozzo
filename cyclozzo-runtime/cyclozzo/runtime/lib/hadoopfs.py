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
import os
import sys
import logging
from cyclozzo.runtime.lib.genhadoopfs import *
from cyclozzo.runtime.lib.genhadoopfs.ttypes import FileStatus, Pathname
from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

log = logging.getLogger(__name__)

class HDFSError(Exception):
	"""Base Exception class for HDFS errors
	"""

class HadoopClient(ThriftHadoopFileSystem.Client):
	def __init__(self, host, port = 10101, timeout_ms = 30000, do_open = 1):
		socket = TSocket.TSocket(host, port)
		socket.setTimeout(timeout_ms)
		self.transport = TTransport.TBufferedTransport(socket)
		protocol = TBinaryProtocol.TBinaryProtocol(self.transport)
		ThriftHadoopFileSystem.Client.__init__(self, protocol)

		if do_open:
			self.open_connection(timeout_ms)

	def open_connection(self, timeout_ms):
		self.transport.open()
		self.do_close = 1

	def close_connection(self):
		if self.do_close:
			self.transport.close()
	
	def open_path(self, path):
		log.debug('hdfs stat %s' % path)
		p = Pathname()
		p.pathname = path
		status = self.stat(p)
		log.debug('group: %s owner: %s permission: %s' % (status.group, 
				status.owner, status.permission))
		if status.isdir:
			log.info('hdfs ls %s' % path)
			return self.listStatus(p)
		
		return status

class HadoopFile(object):
	"""A File-like interface for HDFS files.
	"""
	def __init__(self, hostname, port, filename, mode='r'):
		self._pathname = Pathname(filename)
		self._fs = HadoopClient(hostname, port)
		if mode == 'r':
			self._fh = self._fs.open(self._pathname)
		elif mode == 'w':
			self._fh = self._fs.create(self._pathname)
		else:
			raise HDFSError('Invalid mode: %s' %mode)
		self._seek_pos = 0

	def seek(self, offset):
		self._seek_pos = offset

	def read(self, size=None):
		stat = self._fs.stat(self._pathname)
		if not size:
			size = stat.length
		data = self._fs.read(self._fh, self._seek_pos, size)
		return data
		
	def write(self, data):
		return self._fs.write(self._fh, data)
		
	def close(self):
		self._fs.close(self._fh)
		del self._fh
		self._fs.close_connection()
		del self._fs
		
if __name__ == '__main__':
	logging.basicConfig(level = logging.WARN)
	try:
		hdfs_client = HadoopClient('172.16.5.151')
		
		if len(sys.argv) == 2:
			
			r = hdfs_client.open_path(sys.argv[1])
			if r is FileStatus:
				print '+ dir .'
				print '|'
				print '|- %s block size: %d replication: %d' % (r.path, r.blocksize, r.block_replication)
			else:
				print '+ dir %s' % sys.argv[1]
				print '|'
				for rr in r:
					print '|- %s block size: %d replication: %d' % (rr.path, rr.blocksize, rr.block_replication)
		
		else:
			
			def process_path(hdfs_client, fstatus):
				results = []
				if fstatus.isdir:
					for r in hdfs_client.open_path(fstatus.path):
						results += process_path(hdfs_client, r)
				else:
					print 'Found file %s' % fstatus.path
					results.append(fstatus)
					
				return results
						
			root = hdfs_client.open_path('/')
			for f in root:
				print 'Scaning %s' % f.path
				results = process_path(hdfs_client, f)
				print '%d files found' % len(results)
				total_block_size = reduce(lambda a, b: a + b.blocksize, results, 0)
				print 'total blocks size: %d' % total_block_size
	finally:
		hdfs_client.close_connection()