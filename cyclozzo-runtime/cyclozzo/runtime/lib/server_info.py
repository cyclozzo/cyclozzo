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
#Script for updating Server Information.
#
#Author: Sreejith K

from cyclozzo.runtime.model import Server
from cyclozzo.runtime.lib.ssh import SimpleClient
import logging

log = logging.getLogger(__name__)

class ServerInfo():

	def __init__(self, ssh):
		"""
		Initialize using server id
		"""
		self.ssh = ssh

	def get_os(self):
		"""
		OS Name (eg. Ubuntu 9.10, CentOS 5.4 etc)
		"""
		rc, out = self.ssh.execute_command('cat /etc/issue')
		if rc != 0:
			log.debug('SeverInfo().get_disks() failed with code %s' %rc)
			return 'Unknown'
		else:
			os = out.split('\n')[0].strip()[:-5]
			return os

	def get_disks(self):
		"""
		Return disk partitions and their size {'/dev/sda' : 450000}
		"""
		rc, out = self.ssh.execute_command('cat /proc/partitions')
		disks = {}
		if rc != 0:
			log.debug('SeverInfo().get_disks() failed with code %s out:%s' %(rc, out))
			return {}
		else:
			lines = [line.strip().split() for line in out.split('\n')]
			for line in lines[2:-1]:
				disks[line[3]] = int(line[2])
			return disks

	def get_cpus(self):
		"""
		Return cpu info {0 : ['6', 'Intel(R) Core(TM)2 Quad  CPU   Q8200  @ 2.33GHz', 2003]}
		"""
		rc, out = self.ssh.execute_command('cat /proc/cpuinfo')
		cpus = {}
		if rc != 0:
			log.debug('SeverInfo().get_cpus() failed with code %s out: %s' %(rc, out))
			return {}
		else:
			lines = [line.strip().split(':') for line in out.split('\n')]
			for line in lines:
				if line == ['']:
					continue
				prop, value = [part.strip() for part in line]
				if prop == 'processor':
					proc_num = int(value)
					cpus[proc_num] = []
				if prop == 'cpu family':
					cpus[proc_num].append(value)
				if prop == 'model name':
					cpus[proc_num].append(unicode(value))
				if prop == 'cpu MHz':
					cpus[proc_num].append(int(float(value)))
			return cpus

	def get_memory(self):
		"""
		Return /proc/meminfo in a dictionary
		"""
		rc, out = self.ssh.execute_command('cat /proc/meminfo')
		mem = {}
		if rc != 0:
			log.debug('SeverInfo().get_memory() failed with code %s out: %s' %(rc, out))
			return {}
		else:
			lines = [line.strip().split(':') for line in out.split('\n')]
			for line in lines:
				if len(line) > 1:
					prop, value = [sec.strip() for sec in line]
					mem[prop] = value
			return mem

	def get_nics(self):
		# TODO: Fix this
		"""
		Return Nic information in a dictionary. 
			{eth0 : ['00:80:48:62:04:e3', '10.10.10.40', '255.255.0.0']}
		"""
		rc, out = self.ssh.execute_command('ifconfig')
		nics = {}
		if rc != 0:
			log.debug('SeverInfo().get_nics() failed with code %s out: %s' %(rc, out))
			return {}
		else:
			lines = [line.strip() for line in out.split('\n')]
			nics = []
			for line in lines:
				segs = line.split(' ')
				first = segs[0] 
				if len(first) > 0:
					if 'eth' in first or first == 'lo':
						last = segs[len(segs) - 1]
						nic = [first, last]
						nics.append(nic)
					if first == 'inet' and nic[0] != 'lo':
						ip = segs[1].strip().split(':')[1]
						mask = segs[5].strip().split(':')[1]
						nic.append(ip)
						nic.append(mask)
			return nics


if __name__ == '__main__':
	si = ServerInfo(1)
	disks = si.get_disks()
	print 'Disks:', disks
