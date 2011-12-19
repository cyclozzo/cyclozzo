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
# @author: stanly
# Configuration access class


import logging
import os
import sys

from ConfigParser import SafeConfigParser
from yaml import load, dump
try:
	from yaml import CLoader as Loader
	from yaml import CDumper as Dumper
except ImportError:
	from yaml import Loader, Dumper

log = logging.getLogger(__name__)

"""Application id, received after sing-in"""
__app_id = None

__yaml_conf = None


class Configuration:
	def __init__ (self, fileName):
		cp = SafeConfigParser()
		cp.read(fileName)
		self.__parser = cp
		self.fileName = fileName

	def isSection(self, name):
		p = self.__parser
		return name in p.sections()
		
	def __getattr__ (self, name):
		if name in self.__parser.sections():
			return Section(name, self.__parser)
		else:
			return None
			
	def __str__ (self):
		p = self.__parser
		result = []
		result.append('<Configuration from %s>' % self.fileName)
		for s in p.sections():
			result.append('[%s]' % s)
			for o in p.options(s):
				result.append('%s=%s' % (o, p.get(s, o)))
		return '\n'.join(result)


class Section:
	def __init__ (self, name, parser):
		self.name = name
		self.__parser = parser
	def __getattr__ (self, name):
		return self.__parser.get(self.name, name)


class ApplicationConfiguration(object):
	def __init__(self, file_name):
		self.data = load(file(file_name, 'r'), Loader=Loader)
		self.file_name = file_name
		
	def __str__ (self):
		return 'YAML Config (%s)' % self.file_name
		
	def __repr__(self):
		return str(self)
	
	def __getattr__(self, name):
		try:
			return self.data[name]
		except KeyError:
			return None


def get_yaml():
	global __yaml_conf
	if __yaml_conf is None:
		__yaml_conf = ApplicationConfiguration(os.path.join(os.path.dirname(sys.argv[0]) , 'app.yaml'))
	return __yaml_conf


def set_yaml(yaml_conf):
	global __yaml_conf
	__yaml_conf = yaml_conf


"""Get or generate new application id"""
def get_app_id():
	if get_yaml().provider == 'api' or\
			get_yaml().provider == 'boost':
		global __app_id
		if not __app_id:
			#fixme
			#try to get real app id here
			return get_yaml().application

			raise NotSignedInError('app id is empty')
		return __app_id
	else:
		return get_yaml().application


def set_app_id(id):
	global __app_id
	__app_id = id


"""
Returns api or sdk module instance according to
settings in config file
"""
def get_provider():
	#check loaded
	provider_module = get_yaml().provider
	if not provider_module:
		provider_module = 'sdk'
	module_name = 'cyclozzo.sdk.db.' + provider_module
	try:
		return sys.modules[module_name]
	except KeyError:
		pass
	#load module
	try:
		__import__(module_name)
		return sys.modules[module_name]
	except ImportError, ie:
		print 'Failed to import %s: %s' % (module_name, ie)
		raise SystemExit


if __name__ == '__main__':
	config = Configuration('config.ini')
	print config.dhcp.router
	print config.dhcp.dns
	print config.dhcp.domainName
	print config.dhcp.ntp
	print config.dhcp.defaultBoot
	print config.dhcp.listenPort
	print config.dhcp.emitPort
