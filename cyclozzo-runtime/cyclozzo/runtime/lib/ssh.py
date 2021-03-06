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
#Cyclozzo SSH Client library
#@author: Stanislav Yudin

import sys, os, logging
from cyclozzo.runtime.lib.cmnd import run_command
from subprocess import PIPE

class SimpleClient(object):
	def __init__(self, host, login = None, log = None):
		# parse login@hostname
		if "@" in host and not login:
			login, host = host.split("@")

		if not login:
			login = "cyclozzo"
		self.privkey_path = os.path.join('/home', login, '.ssh/id_dsa')
		
		if log:
			self.log = log
		else:
			self.log = logging.getLogger(__name__)
			
		self.host = host
		self.login = login
		host_login = "%s@%s" % (login, host)
		self.ssh_cmd = ['ssh',
				'-i', self.privkey_path,
				'-p 22',
				'-oStrictHostKeyChecking=no',
				'-oBatchMode=yes', 
				'-oLogLevel=ERROR',
				'-oServerAliveInterval=15',
				'-oPreferredAuthentications=publickey',
				'-oUserKnownHostsFile=/dev/null',
				host_login]
				
	def _build_cmd(self, cmd):
		if type(cmd) == type(""):
			wcmd = [cmd]
		else:
			wcmd = cmd

		# escape cpecial characters
		new_wcmd = []
		for arg in wcmd:
			earg = arg
			for ch in ["\\", "$", "\"", "'", ";",
				"|", "&", "[", "]", "{", "}"]:
				earg = earg.replace(ch, "\\" + ch)
			new_wcmd.append(earg)
		wcmd = new_wcmd
		return self.ssh_cmd + wcmd

	def execute_command(self, cmd, no_wait = False):
		"""
		Run cmd on the remote host.

		cmd is either a string or a sequence of strings
		other parameters are the same as in subprocess.Popen
		
		Returns tuple (int, string) of child exit code and child's output to
		stdout and stderr as string
		"""
		if self.log:
			self.log.info('SSH: execute_command "%s"' % cmd)
		return run_command(self._build_cmd(cmd), log = self.log,
			no_wait = no_wait, stdout = PIPE, stderr = PIPE, stdin = sys.stdin)

if __name__ == "__main__":
	#positive
	cl = SimpleClient('root@172.16.75.50')
	res = cl.execute_command(['ls', '/'])
	print 'Exit code:', res[0]
	print 'Output:', res[1]
	
	#negative
	cl2 = SimpleClient('hui@172.16.75.50')
	cl2.execute_command('ls /', stdout = sys.stdout, stderr = sys.stderr)
