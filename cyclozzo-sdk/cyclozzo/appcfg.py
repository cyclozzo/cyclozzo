#! /usr/bin/env python
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
#	Copyright (c) 2009, K7 Computing
#	Author	:	Sreejith K
#
"""
Tool for deploying apps to an app server.
"""

import sys
import os
import logging
import optparse
import urllib
import urllib2
import hashlib
import getpass
import uuid
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from cyclozzo.archive import pack

class AppCfgApp(object):
	"""Singleton class to wrap AppCfg tool functionality.

	This class is responsible for parsing the command line and executing
	the desired action on behalf of the user.  Processing files and
	communicating with the server is handled by other classes.

	Attributes:
		actions: A dictionary mapping action names to Action objects.
		action: The Action specified on the command line.
		parser: An instance of optparse.OptionParser.
		options: The command line options parsed by 'parser'.
		argv: The original command line as a list.
		args: The positional command line args left over after parsing the options.
		raw_input_fn: Function used for getting raw user input, like email.
		password_input_fn: Function used for getting user password.
		error_fh: Unexpected HTTPErrors are printed to this file handle.

	Attributes for testing:
		parser_class: The class to use for parsing the command line.  Because
	  		OptionsParser will exit the program when there is a parse failure, it
	  		is nice to subclass OptionsParser and catch the error before exiting.
	"""

	def __init__(self, argv, parser_class=optparse.OptionParser,
					raw_input_fn=raw_input,
					password_input_fn=getpass.getpass,
					error_fh=sys.stderr,
					update_check_class=None):#UpdateCheck):
		
		self.parser_class = parser_class
		self.argv = argv
		self.raw_input_fn = raw_input_fn
		self.password_input_fn = password_input_fn
		self.error_fh = error_fh
		self.update_check_class = update_check_class

		self.parser = self._GetOptionParser()

		for action in self.actions.itervalues():
			action.options(self, self.parser)

		self.options, self.args = self.parser.parse_args(argv[1:])

		if len(self.args) < 1:
			self._PrintHelpAndExit()

		if self.args[0] not in self.actions:
			self.parser.error('Unknown action \'%s\'\n%s' %
					(self.args[0], self.parser.get_description()))
		action_name = self.args.pop(0)
		self.action = self.actions[action_name]

		self.parser, self.options = self._MakeSpecificParser(self.action)

		if self.options.help:
			self._PrintHelpAndExit()

		if self.options.verbose == 2:
			logging.getLogger().setLevel(logging.INFO)
		elif self.options.verbose == 3:
			logging.getLogger().setLevel(logging.DEBUG)

		global verbosity
		verbosity = self.options.verbose

	def Run(self):
		"""Executes the requested action.

		Catches any HTTPErrors raised by the action and prints them to stderr.

		Returns:
			1 on error, 0 if successful.
		"""
		try:
			self.action(self)
		except urllib2.HTTPError, e:
			body = e.read()
			print >>self.error_fh, ('Error %d: --- begin server output ---\n'
									'%s\n--- end server output ---' %
									(e.code, body.rstrip('\n')))
			return 1
		#except yaml_errors.EventListenerError, e:
			#print >>self.error_fh, ('Error parsing yaml file:\n%s' % e)
			#return 1
		return 0

	def _GetOptionParser(self):
		"""Creates an OptionParser with generic usage and description strings.

		Returns:
			An OptionParser instance.
		"""

		class Formatter(optparse.IndentedHelpFormatter):
			"""Custom help formatter that does not reformat the description."""

			def format_description(self, description):
				"""Simple Formatter"""
				return description + '\n'

		desc = self._GetActionDescriptions()
		desc = ('Action must be one of:\n%s'
				'Use \'help <action>\' for a detailed description.') % desc

		parser = self.parser_class(usage='%prog [options] <action>',
									description=desc,
									formatter=Formatter(),
									conflict_handler='resolve')
		parser.add_option('-h', '--help', action='store_true',
							dest='help', help='Show the help message and exit.')
		parser.add_option('-q', '--quiet', action='store_const', const=0,
							dest='verbose', help='Print errors only.')
		parser.add_option('-v', '--verbose', action='store_const', const=2,
							dest='verbose', default=1,
							help='Print info level logs.')
		parser.add_option('--noisy', action='store_const', const=3,
							dest='verbose', help='Print all logs.')
		parser.add_option('-s', '--server', action='store', dest='server',
							default=None,
							metavar='SERVER', help='The server to connect to.')
		parser.add_option('--secure', action='store_true', dest='secure',
							default=False,
							help='Use SSL when communicating with the server.')
		parser.add_option('-e', '--email', action='store', dest='email',
							metavar='EMAIL', default=None,
							help='The username to use. Will prompt if omitted.')
		parser.add_option('-H', '--host', action='store', dest='host',
							metavar='HOST', default=None,
							help='Overrides the Host header sent with all RPCs.')
		parser.add_option('--no_cookies', action='store_false',
							dest='save_cookies', default=True,
							help='Do not save authentication cookies to local disk.')
		parser.add_option('--passin', action='store_true',
							dest='passin', default=False,
							help='Read the login password from stdin.')
		return parser

	def _MakeSpecificParser(self, action):
		"""Creates a new parser with documentation specific to 'action'.

		Args:
			action: An Action instance to be used when initializing the new parser.

		Returns:
			A tuple containing:
			parser: An instance of OptionsParser customized to 'action'.
			options: The command line options after re-parsing.
		"""
		parser = self._GetOptionParser()
		parser.set_usage(action.usage)
		parser.set_description('%s\n%s' % (action.short_desc, action.long_desc))
		action.options(self, parser)
		options, unused_args = parser.parse_args(self.argv[1:])
		return parser, options

	def _GetActionDescriptions(self):
		"""Returns a formatted string containing the short_descs for all actions."""
		action_names = self.actions.keys()
		action_names.sort()
		desc = ''
		for action_name in action_names:
			desc += '  %s: %s\n' % (action_name, self.actions[action_name].short_desc)
		return desc

	def _PrintHelpAndExit(self, exit_code=2):
		"""Prints the parser's help message and exits the program.

		Args:
			exit_code: The integer code to pass to sys.exit().
		"""
		self.parser.print_help()
		sys.exit(exit_code)


	def _UpdateOptions(self, parser):
		"""Adds update-specific options to 'parser'.

		Args:
			parser: An instance of OptionsParser.
		"""
		parser.add_option('-S', '--max_size', type='int', dest='max_size',
							default=10485760, metavar='SIZE',
							help='Maximum size of a file to upload.')
		parser.add_option('-p', '--password', type='string', dest='password',
							metavar='PASSWD',
							help='User password for upload')
	
	def Update(self):
		"""Updates and deploys a new appversion."""
		if len(self.args) != 1:
			self.parser.error('Expected a single <directory> argument.')

		path = self.args[0]
		if not os.path.exists(path):
			StatusUpdate('%s doesn\'t exist' % path)
			return
		
		if not self.options.server:
			self.options.server = self.raw_input_fn('Target controller server: ')
		if not self.options.email:
			self.options.email = self.raw_input_fn('Enter Username(Email): ')
		
		if not self.options.password:
			self.options.password = self.password_input_fn('Password: ')

		url = 'http://%s/api/upload' % self.options.server
		StatusUpdate('Uploading to %s' % url)
		tarball = pack(path, dest_file = os.path.join('/tmp', str(uuid.uuid4()).replace('-', '')) )
		StatusUpdate('Created tmp file at %s' % tarball)
		
		tarball_data  = open(tarball, 'rb')

		register_openers()
		datagen, headers = multipart_encode({
							"uploaded_app" : tarball_data,
							"owner" : self.options.email,
							"password_hash" : hashlib.md5(self.options.password).hexdigest()})
		# Create the Request object
		request = urllib2.Request(url, datagen, headers)
		# Response back from the server....
		answer = urllib2.urlopen(request).read()
		StatusUpdate(answer)

	def UpdateIndexes(self):
		"""If the index.yaml file defines an index that doesn't exist yet on 
		K7 Platform, it creates the new index"""
		
		index_file = os.path.join(self.args[0], 'index.yaml')
	
	class Action(object):
		"""Contains information about a command line action.

		Attributes:
			function: The name of a function defined on AppCfg or its subclasses
				that will perform the appropriate action.
			usage: A command line usage string.
			short_desc: A one-line description of the action.
			long_desc: A detailed description of the action.  Whitespace and
				formatting will be preserved.
			options: A function that will add extra options to a given OptionParser
				object.
		"""

		def __init__(self, function, usage, short_desc, long_desc='',
						options=lambda obj, parser: None):
			"""Initializer for the class attributes."""
			self.function = function
			self.usage = usage
			self.short_desc = short_desc
			self.long_desc = long_desc
			self.options = options

		def __call__(self, appcfg):
			"""Invoke this Action on the specified AppCfg.

			This calls the function of the appropriate name on AppCfg, and
			respects polymophic overrides.

			Args:
				appcfg: The appcfg to use.
			Returns:
				The result of the function call.
			"""
			method = getattr(appcfg, self.function)
			return method()

	actions = {

			'help': Action(
				function='Help',
				usage='%prog help <action>',
				short_desc='Print help for a specific action.'),

			'update': Action(
				function='Update',
				usage='%prog [options] update <directory>',
				options=_UpdateOptions,
				short_desc='Create or update an app version.',
				long_desc="""
Specify a directory that contains all of the files required by
the app, and appcfg.py will create/update the app version referenced
in the app.yaml file at the top level of that directory.  appcfg.py
will follow symlinks and recursively upload all files to the server.
Temporary or source control files (e.g. foo~, .svn/*) will be skipped."""),

#			'update_cron': Action(
#				function='UpdateCron',
#				usage='%prog [options] update_cron <directory>',
#				short_desc='Update application cron definitions.',
#				long_desc="""
#The 'update_cron' command will update any new, removed or changed cron
#definitions from the optional cron.yaml file."""),
#
			'update_indexes': Action(
				function='UpdateIndexes',
				usage='%prog [options] update_indexes <directory>',
				short_desc='Update application indexes.',
				long_desc="""
				The 'update_indexes' command will add additional indexes which are not currently
in production as well as restart any indexes that were not completed."""),

#			'update_queues': Action(
#				function='UpdateQueues',
#				usage='%prog [options] update_queues <directory>',
#				short_desc='Update application task queue definitions.',
#				long_desc="""
#The 'update_queue' command will update any new, removed or changed task queue
#definitions from the optional queue.yaml file."""),
#
#			'vacuum_indexes': Action(
#				function='VacuumIndexes',
#				usage='%prog [options] vacuum_indexes <directory>',
#				options=_VacuumIndexesOptions,
#				short_desc='Delete unused indexes from application.',
#				long_desc="""
#The 'vacuum_indexes' command will help clean up indexes which are no longer
#in use.  It does this by comparing the local index configuration with
#indexes that are actually defined on the server.  If any indexes on the
#server do not exist in the index configuration file, the user is given the
#option to delete them."""),
#
#			'rollback': Action(
#				function='Rollback',
#				usage='%prog [options] rollback <directory>',
#				short_desc='Rollback an in-progress update.',
#				long_desc="""
#The 'update' command requires a server-side transaction.  Use 'rollback'
#if you get an error message about another transaction being in progress
#and you are sure that there is no such transaction."""),
#
#			'request_logs': Action(
#				function='RequestLogs',
#				usage='%prog [options] request_logs <directory> <output_file>',
#				options=_RequestLogsOptions,
#				short_desc='Write request logs in Apache common log format.',
#				long_desc="""
#The 'request_logs' command exports the request logs from your application
#to a file.  It will write Apache common log format records ordered
#chronologically.  If output file is '-' stdout will be written."""),
#
#			'cron_info': Action(
#				function='CronInfo',
#				usage='%prog [options] cron_info <directory>',
#				options=_CronInfoOptions,
#				short_desc='Display information about cron jobs.',
#				long_desc="""
#The 'cron_info' command will display the next 'number' runs (default 5) for
#each cron job defined in the cron.yaml file."""),
#
#			'upload_data': Action(
#				function='PerformUpload',
#				usage='%prog [options] upload_data <directory>',
#				options=_PerformUploadOptions,
#				short_desc='Upload data records to datastore.',
#				long_desc="""
#The 'upload_data' command translates input records into datastore entities and
#uploads them into your application's datastore."""),

#			'download_data': Action(
#				function='PerformDownload',
#				usage='%prog [options] download_data <directory>',
#				options=_PerformDownloadOptions,
#				short_desc='Download entities from datastore.',
#				long_desc="""
#The 'download_data' command downloads datastore entities and writes them to
#file as CSV or developer defined format."""),
#
			}

def StatusUpdate(msg):
	"""Print a status message to stderr.

	If 'verbosity' is greater than 0, print the message.

	Args:
		msg: The string to print.
	"""
	if verbosity > 0:
		print >>sys.stderr, msg

def FileIterator(base, separator=os.path.sep):
	"""Walks a directory tree, returning all the files. Follows symlinks.

	Args:
		base: The base path to search for files under.
		separator: Path separator used by the running system's platform.

	Yields:
		Paths of files found, relative to base.
	"""
	dirs = ['']
	while dirs:
		current_dir = dirs.pop()
		for entry in os.listdir(os.path.join(base, current_dir)):
			name = os.path.join(current_dir, entry)
			fullname = os.path.join(base, name)
			if os.path.isfile(fullname):
				if separator == '\\':
					name = name.replace('\\', '/')
				yield name
			elif os.path.isdir(fullname):
				dirs.append(name)


def main(argv):
	logging.basicConfig(format=('%(asctime)s %(levelname)s %(filename)s:'
							'%(lineno)s %(message)s '))

	try:
		result = AppCfgApp(argv).Run()
		if result:
			sys.exit(result)
	except KeyboardInterrupt:
		StatusUpdate('Interrupted by User')
		sys.exit(1)

if __name__ == '__main__':
	main(sys.argv)
