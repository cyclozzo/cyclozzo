#! /usr/bin/env python
#
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
# Register available Cyclozzo apis.
#
# @author: Sreejith K
# Created on 5th April 2010

import os
import tempfile
import logging

from cyclozzo.apps.tools import appserver

log = logging.getLogger(__name__)

def register_apis(config):
	"""Register apis for an application. Provide either YAML object or a
	dictionary.
	"""
	def yaml_to_dict(config):
		d = {}
		for attr in dir(config):
			if not attr.startswith('_'):
				value = getattr(config, attr)
				d[attr] = value
		return d['data']

	if not type(config) == type(dict):
		config = yaml_to_dict(config)
		
	login_url = config.get('login_url', '/_ah/login')
	serve_address = config.get('address', 'localhost')
	require_indexes = eval(config.get('require_indexes', 'False'))
	allow_skipped_files = eval(config.get('allow_skipped_files', 'False'))
	static_caching = eval(config.get('static_caching', 'True'))

	config['login_url'] = login_url
	config['datastore_path'] = os.path.join(tempfile.gettempdir(),
												'dev_appserver.datastore')
	config['clear_datastore'] = False

	app_id = config.get('application', 'cyclozzo')
	appserver.SetupStubs(app_id, **config)


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)

	class FakeConfig(object):
		application = 'test'
		ht_config = '/etc/cyclozzo/hypertable.cfg'
		provider = 'thrift'

	register_apis(FakeConfig())
	
	from cyclozzo.apps.ext import db
	
	class FooModel(db.Model):
		foo = db.IntegerProperty()
		bar = db.StringProperty()
		baz = db.TextProperty()
		
	class BarModel(db.Model):
		foo = db.ReferenceProperty(FooModel)
		bar = db.ListProperty(int)
	
	# save some entities
	Foo = FooModel(key_name = 'FooBarBaz')
	Foo.foo = 1
	Foo.bar = 'bar'
	Foo.baz = u'baz'
	logging.debug('Entity saved with key: %s' %Foo.put())
	Foo = FooModel(key_name = 'BarBazFoo')
	Foo.foo = 2
	Foo.bar = 'bar'
	Foo.baz = u'baz'
	logging.debug('Entity saved with key: %s' %Foo.put())
	Foo = FooModel(key_name = 'BazFooBar')
	Foo.foo = 3
	Foo.bar = 'bar'
	Foo.baz = u'baz'
	logging.debug('Entity saved with key: %s' %Foo.put())

	# make some queries
	[logging.debug(Foo.foo) for Foo in FooModel.all().order('foo')]
	[logging.debug(Foo.foo) for Foo in FooModel.all().filter('foo =', 56)]
	[logging.debug(Foo.foo) for Foo in FooModel.all().filter('foo =', 1)]
	
	# make use of query cursor
	query =  FooModel.all().order('foo')
	first = query.fetch(1)[0]
	log.debug(first.foo)
	assert first.foo == 1L
	cursor = query.cursor()
	query.with_cursor(cursor)
	next = query.fetch(1)[0]
	log.debug(next.foo)
	assert next.foo == 2L
	cursor = query.cursor()
	query.with_cursor(cursor)
	next = query.fetch(1)[0]
	log.debug(next.foo)
	assert next.foo == 3L

	# use get_by_key_name
	Foo_Get = FooModel.get_by_key_name('FooBarBaz')
	logging.debug('Foo_Get.foo: %r' %Foo_Get.foo)
	logging.debug('Foo_Get.bar: %r' %Foo_Get.bar)
	logging.debug('Foo_Get.baz: %r' %Foo_Get.baz)
	
	# delete this entity
	Foo_Get.delete()
	
	Foo_Get = FooModel.get_by_key_name('BarBazFoo')
	logging.debug('Foo_Get.foo: %r' %Foo_Get.foo)
	logging.debug('Foo_Get.bar: %r' %Foo_Get.bar)
	logging.debug('Foo_Get.baz: %r' %Foo_Get.baz)
	
	# delete this entity
	Foo_Get.delete()
	
	Foo_Get = FooModel.get_by_key_name('BazFooBar')
	logging.debug('Foo_Get.foo: %r' %Foo_Get.foo)
	logging.debug('Foo_Get.bar: %r' %Foo_Get.bar)
	logging.debug('Foo_Get.baz: %r' %Foo_Get.baz)
	
	# add a reference property
	Bar = BarModel(key_name = 'FooReference')
	Bar.foo = Foo_Get
	Bar.bar = [1, 2, 3, 4]
	Bar.put()
	Bar_Get = BarModel.get_by_key_name('FooReference')
	assert isinstance(Bar_Get.foo, db.Model)
	assert Bar_Get.foo.foo == Foo_Get.foo
	assert isinstance(Bar_Get.bar, list)
	assert Bar_Get.bar == [1, 2, 3, 4]

	# delete this entity
	Bar_Get.delete()
	Foo_Get.delete()
	
	# saving without key_name
	Foo = FooModel()
	Foo.foo = 1
	Foo.bar = 'bar'
	Foo.baz = u'baz'
	key = Foo.save()
	logging.debug('Entity saved with key: %s' %key)
	# query
	[logging.debug(Foo.foo) for Foo in FooModel.all().order('foo')]
	# use Model.get
	Foo = FooModel.get(key)
	assert Foo.foo == 1L
	Foo.delete()
	
	# drop tables
	FooModel.drop_table()
	BarModel.drop_table()
