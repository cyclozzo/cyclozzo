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
# Cyclozzo Satellite AppServer
# @authors: Stanislav Yudin, Sreejith K

import os
import sys
import logging
import tempfile
import signal
import datetime
import inspect
import traceback
import functools
import threading, thread
from time import sleep, time
from optparse import OptionParser
from subprocess import PIPE


from cyclozzo.runtime.lib.config import ApplicationConfiguration, get_yaml, set_yaml
from cyclozzo.metrics import report_app_log, report_api_metrics, monitor_cpu_mcycles
from cyclozzo.runtime.lib import enable_log
from cyclozzo.runtime.lib.daemon import Daemon
from cyclozzo.runtime.lib.cmnd import run_command


import tornado.ioloop
import tornado.web

from cyclozzo.apps.api import yaml_errors
from cyclozzo.apps.dist import py_zipimport
from cyclozzo.apps.tools import appserver
from cyclozzo.apps.tools import os_compat

SDK_PATH = os.path.dirname(
						os.path.dirname(
									os.path.dirname(
												os.path.dirname(os_compat.__file__)
												)
									)
						)


log = logging.getLogger(__name__)
#The one and only instance of AppDaemon
the_daemon = None
#Application daemon/http server implementation
class AppDaemon(Daemon):
	def __init__(self, yaml, app_path, server_key, port, master_addr, master_port):
		#check instance
		global the_daemon
		if the_daemon:
			raise Exception('Trying to create another instance of app in same process!')

		self.app_path = os.path.abspath(app_path)
		self.app_name = os.path.basename(self.app_path)
		self.server_key = server_key
		self.port = int(port)
		self.master_addr = master_addr
		self.master_port = master_port

		self.logfile = os.path.join(self.app_path, 'logfile')
		self.pidfile = os.path.join(self.app_path, 'pidfile')

		#this is satellite yaml config
		self.config = yaml
		enable_log(self.logfile, debug = self.config.debug_mode)
		super(AppDaemon, self).__init__(pidfile = self.pidfile)

		#set daemon instance
		the_daemon = self
		# tell this daemon not to register altexit for cleaning up pid
		self.do_cleanup = False

	def stop_application(self):
		log.info('stopping all callbacks')
		self.log_callback.stop()
		self.api_callback.stop()
		self.cpu_callback.stop()
		log.info('stopping Tornado HTTPSserver')
		self.http_server.stop()
		log.info('stopping Tornado ioloop')
		tornado.ioloop.IOLoop.instance().add_timeout(time() + 2, tornado.ioloop.IOLoop.instance().stop)
		log.info('http server stoped gracefully')
		try:
			self.delpid()
		except OSError:
			pass
		sys.exit(0)

	def run_application(self):
		log.debug('pidfile: %s' % self.pidfile)
		log.debug('runing app on port %d' % self.port)

		app_yaml = os.path.join(self.app_path, 'app.yaml')
		if not os.path.exists(app_yaml):
			log.error('there is no app.yaml at %s' % app_yaml)
			return

		#this is application yaml config
		yaml = ApplicationConfiguration(app_yaml)
		sys.path.insert(0, self.app_path)

		if yaml.runtime == 'python':
			yaml.provider = 'boost'
			set_yaml(yaml)

			if self.config.enable_logging:
				enable_logging = eval(self.config.enable_logging)
				appserver.HardenedModulesHook.ENABLE_LOGGING = enable_logging

			def yaml_to_dict(config):
				d = {}
				for attr in dir(config):
					if not attr.startswith('_'):
						value = getattr(config, attr)
						d[attr] = value
				return d['data']

			option_dict = yaml_to_dict(self.config)

			if self.config.debug_mode:
				log_level = logging.DEBUG
			else:
				log_level = logging.INFO
			login_url = option_dict.get('login_url', '/_ah/login')
			template_dir = option_dict.get('template_dir', os.path.join(SDK_PATH, 'templates'))
			serve_address = option_dict.get('address', 'localhost')
			require_indexes = eval(option_dict.get('require_indexes', 'False'))
			allow_skipped_files = eval(option_dict.get('allow_skipped_files', 'False'))
			static_caching = eval(option_dict.get('static_caching', 'True'))
			cpu_monitor_interval = int(option_dict.get('cpu_monitor_interval', 1000))

			option_dict['root_path'] = os.path.realpath(self.app_path)
			option_dict['login_url'] = login_url
			option_dict['datastore_path'] = os.path.join(tempfile.gettempdir(),
														'dev_appserver.datastore')
			option_dict['clear_datastore'] = False
			option_dict['port'] = self.port

			logging.getLogger().setLevel(log_level)

			config = None
			try:
				config, matcher = appserver.LoadAppConfig(self.app_path, {})
			except yaml_errors.EventListenerError, e:
				log.error('Fatal error when loading application configuration:\n' +
						str(e))
				return 1
			except appserver.InvalidAppConfigError, e:
				log.error('Application configuration file invalid:\n%s', e)
				return 1

			try:
				appserver.SetupStubs(config.application, **option_dict)
			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				log.error(str(exc_type) + ': ' + str(exc_value))
				log.debug(''.join(traceback.format_exception(
								exc_type, exc_value, exc_traceback)))
				return 1

			self.http_server = appserver.CreateServer(
												self.app_path,
												login_url,
												self.config,
												matcher,
												config.admin_name,
												template_dir,
												sdk_dir=SDK_PATH,
												require_indexes=require_indexes,
												allow_skipped_files=allow_skipped_files,
												static_caching=static_caching)

			def stop_gracefully(signum, frame):
				"""SIGTERM handler to stop application gracefully
				"""
				self.stop_application()

			signal.signal(signal.SIGTERM, stop_gracefully)

			log.info('Running application %s on port %d: http://%s:%d',
					config.application, self.port, serve_address, self.port)

			mcycles_limit = yaml.mcycles_per_minute or 64000000
			# create callables for periodic callbacks.
			log_reporter = functools.partial(report_app_log, self.master_addr, self.master_port, yaml.application, self.port, self.server_key)
			api_reporter = functools.partial(report_api_metrics, self.master_addr, self.master_port, yaml.application, self.server_key, self.port)
			cpu_monitor = functools.partial(monitor_cpu_mcycles, self.master_addr, self.master_port, yaml.application, mcycles_limit, cpu_monitor_interval)

			try:
				self.http_server.listen(self.port)
				io_loop = tornado.ioloop.IOLoop.instance()
				# set periodic callbacks for api and log reporter.
				self.log_callback = tornado.ioloop.PeriodicCallback(log_reporter, 5000)
				self.api_callback = tornado.ioloop.PeriodicCallback(api_reporter, 10000)
				self.cpu_callback = tornado.ioloop.PeriodicCallback(cpu_monitor, cpu_monitor_interval)
				self.log_callback.start()
				self.api_callback.start()
				self.cpu_callback.start()
				log.info('starting tornado IO loop')
				io_loop.start()
			except KeyboardInterrupt:
				log.info('Server interrupted by user, terminating')
				self.stop_application()
			except:
				exc_info = sys.exc_info()
				info_string = '\n'.join(traceback.format_exception(*exc_info))
				log.error('Error encountered:\n%s\nNow terminating.', info_string)
				sys.exit(-3)

		elif yaml.runtime == 'java':
			java_util_path = os.path.join(sys.path[0], 'java_util.sh')
			if not os.path.exists(java_util_path):
				log.error('java utility module is not found at %s' % java_util_path)
				sys.exit(-2)

			log.debug('spawning java utility script from %s' % java_util_path)
			rc, out = run_command(['sh', java_util_path], stderr = PIPE, stdout = PIPE)
			if rc != 0:
				log.error('Failed to start java application, code: %d, %s' % (rc, out) )
			else:
				log.info('Java application was spawned successfully.')
			sys.exit(rc)

		else:
			log.fatal('Runtime %s is NOT supported' % yaml.runtime)
			sys.exit(-5)

	def run(self):
		log.debug('--------- application %s started on %s -----------'
				% ( self.app_path, datetime.datetime.now()) )
		self.run_application()

if __name__ == '__main__':

	def for_each_instance(func):
		count = 0
		for app_name in os.listdir(yaml.apps_folder):
			if '.' in app_name:
				continue
			for rev in os.listdir(os.path.join(yaml.apps_folder, app_name)):
				rev_path = os.path.join(yaml.apps_folder, app_name, rev)
				if not os.path.isdir(rev_path):
					continue
				for port in os.listdir(rev_path):
					inst_path = os.path.join(rev_path, port)
					if not os.path.isdir(inst_path):
						continue
					if not func(yaml, app_name, rev, port):
						print 'Error: Failed at %s(%s)' % (func.__name__, inst_path)
						return count
					else:
						count += 1
		return count

	def get_pid(app_path):
			dp = os.path.join(app_path, 'pidfile')
			if os.path.exists(dp):
				f = open(dp, 'r')
				dpid = int(f.readline())
				f.close()
				return dpid

			else:
				return '-'


	this_dir = os.path.dirname(os.path.abspath(inspect.getfile( inspect.currentframe())))
	yaml_path = os.path.join(this_dir, 'appserver.yaml')
	if not os.path.exists(yaml_path):
		print 'No configuration yaml for satellite found.'
		sys.exit(1)

	yaml = ApplicationConfiguration(yaml_path)

	parser = OptionParser()
	parser.add_option("-n", "--name",  help="Application name")
	parser.add_option("-r", "--revision",  help="Application revision")
	parser.add_option("-p", "--port",  help="Listen port number")
	parser.add_option("-k", "--key",  help="Server key")

	parser.add_option("-s", "--start", action="store_true", default=False,
						help="Sends START command")
	parser.add_option("-t", "--stop", action="store_true", default=False,
						help="Sends STOP command")
	parser.add_option("-b", "--debug", action="store_true", default=False,
						help="Sends STOP command")
	parser.add_option("--stopall", action="store_true", default=False,
						help="Stop app running apps")
	parser.add_option("--clear", action="store_true", default=False,
						help="Remove unpacked applications")
	parser.add_option("--status", action="store_true", default=False,
						help="List application instance status")
	parser.add_option("--silent", action="store_true", default=False,
						help="Truns off header and totals for --status. Default: NO")
	parser.add_option("--cleanup", action="store_true", default=False,
						help="Do not remove unpacked app from /var/cyclozzo/apps. Default: NO")
	(options, args) = parser.parse_args()

	if options.stopall:
		print 'Stopping all instances'
		def stop_instance(yaml, name, rev, port):
			app_path = os.path.join(yaml.apps_folder, name, rev, port)
			pid = get_pid(app_path)
			if pid == '-':
				print 'No instance running'
				return True
			print 'Stopping instance with pid %d' % pid
			os.kill(pid, signal.SIGTERM)
			if options.cleanup:
				print 'Removing unpacked app [%s]' % app_path
				os.system('rm -fr %s' % app_path)
			return True

		for_each_instance(stop_instance)

	elif options.clear:
		print 'Creaning up unpacked applications'
		def clear_unpacked(yaml, name, rev, port):
			inst_path = os.path.join(yaml.apps_folder, name, rev, port)
			if os.path.exists(os.path.join(inst_path, 'app.yaml')):
				print 'Removing %s' % inst_path
				if os.system('sudo rm -fr %s' % inst_path) != 0:
					print 'Failed to remove unpacked app at %s' % inst_path
					return False
				return True

		for_each_instance(clear_unpacked)


	elif options.status:
		if not options.silent:
			print 'Instances List'
		def parse_instance_info(yaml, name, rev, port):
			inst_path = os.path.join(yaml.apps_folder, name, rev, port)
			try:
				pid = get_pid(inst_path)
				print ' %s\t| %s\t| %s' % (pid, port, '%s #%s' % (name, rev))
				return True
			except Exception, ex:
				print 'Error: failed to stop: %s' % ex
				return False
		if not options.silent:
			print ' pid\t| port\t| application'

		total = for_each_instance(parse_instance_info)

		if not options.silent:
			print '%d instance(s) totally' % total

	elif not options.name or not options.revision or not options.port:
		print 'Error: Required argument is missing'
		parser.print_help()
		sys.exit(1)
	else:
		print 'Cyclozzo Application Host Service. K7Computing 2009-2010 Copyright.'
		#operate daemon
		try:
			logdir = yaml.logdir
		except Exception:
			logdir = '/var/cyclozzo/logs/'
			print 'Warning: No path specified for logs. Using default location: %s' % logdir

		app_path = os.path.join(yaml.apps_folder,
							options.name,
							str(options.revision),
							str(options.port))
		if not os.path.exists(app_path):
			os.makedirs(app_path)

		if options.start:
			daemon = AppDaemon(yaml, app_path, options.key, options.port, yaml.master_address, yaml.master_port)
			if not options.key:
				print 'Error: Required argument --key is missing'
				parser.print_help()
				sys.exit(1)
			print 'Starting application %s rev.%s on port %s' % (options.name,
														options.revision,
														options.port)
			daemon.start()

		elif options.stop:
			if not options.key:
				options.key = None
			#print 'Stopping application %s rev.%s on port %s' % (options.name,
			#											options.revision,
			#											options.port)
			pid = get_pid(app_path)
			if pid == '-':
				print 'No instance running'
				sys.exit(1)
			print 'Stopping instance with pid %d' % pid
			os.kill(pid, signal.SIGTERM)
			if options.cleanup:
				print 'Removing unpacked app [%s]' % app_path
				os.system('rm -fr %s' % app_path)

		elif options.debug:
			if not options.key:
				print 'Error: Required argument --key is missing'
				parser.print_help()
				sys.exit(1)
			logging.basicConfig(level=logging.DEBUG)
			print 'Debugging Production App Server:	 Application %s rev.%s on port %s' % (options.name,
														options.revision,
														options.port)
			daemon = AppDaemon(yaml, app_path, options.key, options.port, yaml.master_address, yaml.master_port)
			daemon.run_application()

		elif options.log:
			dp = os.path.join(app_path, 'logfile')
			if os.path.exists(dp):
				os.system('cat %s | more' % dp)
			else:
				print 'No logfile found'
				sys.exit(-1)
		else:
			parser.print_help()
			sys.exit(-1)


