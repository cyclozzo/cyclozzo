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

"""Convience functions for the Webapp framework."""





__all__ = ['login_required',
           'run_wsgi_app',
           'add_wsgi_middleware',
           'run_bare_wsgi_app',
           ]

import os
import sys
import wsgiref.util

from cyclozzo.apps.api import users
from cyclozzo.apps.api import lib_config
from cyclozzo.apps.ext import webapp


def login_required(handler_method):
  """A decorator to require that a user be logged in to access a handler.

  To use it, decorate your get() method like this:

    @login_required
    def get(self):
      user = users.get_current_user(self)
      self.response.out.write('Hello, ' + user.nickname())

  We will redirect to a login page if the user is not logged in. We always
  redirect to the request URI, and Google Accounts only redirects back as a GET
  request, so this should not be used for POSTs.
  """
  def check_login(self, *args):
    if self.request.method != 'GET':
      raise webapp.Error('The check_login decorator can only be used for GET '
                         'requests')
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))
      return
    else:
      handler_method(self, *args)
  return check_login


_config_handle = lib_config.register(
    'webapp',
    {'add_wsgi_middleware': lambda app: app})


def run_wsgi_app(application):
  """Runs your WSGI-compliant application object in a CGI environment.

  Compared to wsgiref.handlers.CGIHandler().run(application), this
  function takes some shortcuts.  Those are possible because the
  app server makes stronger promises than the CGI standard.

  Also, this function may wrap custom WSGI middleware around the
  application.  (You can use run_bare_wsgi_app() to run an application
  without adding WSGI middleware, and add_wsgi_middleware() to wrap
  the configured WSGI middleware around an application without running
  it.  This function is merely a convenient combination of the latter
  two.)

  To configure custom WSGI middleware, define a function
  webapp_add_wsgi_middleware(app) to your appengine_config.py file in
  your application root directory:

    def webapp_add_wsgi_middleware(app):
      app = MiddleWareClassOne(app)
      app = MiddleWareClassTwo(app)
      return app

  You must import the middleware classes elsewhere in the file.  If
  the function is not found, no WSGI middleware is added.
  """
  run_bare_wsgi_app(add_wsgi_middleware(application))


def add_wsgi_middleware(application):
  """Wrap WSGI middleware around a WSGI application object."""
  return _config_handle.add_wsgi_middleware(application)


def run_bare_wsgi_app(application):
  """Like run_wsgi_app() but doesn't add WSGI middleware."""
  env = dict(os.environ)
  env["wsgi.input"] = sys.stdin
  env["wsgi.errors"] = sys.stderr
  env["wsgi.version"] = (1, 0)
  env["wsgi.run_once"] = True
  env["wsgi.url_scheme"] = wsgiref.util.guess_scheme(env)
  env["wsgi.multithread"] = False
  env["wsgi.multiprocess"] = False
  result = application(env, _start_response)
  if result is not None:
    for data in result:
      sys.stdout.write(data)


def _start_response(status, headers, exc_info=None):
  """A start_response() callable as specified by PEP 333"""
  if exc_info is not None:
    raise exc_info[0], exc_info[1], exc_info[2]
  print "Status: %s" % status
  for name, val in headers:
    print "%s: %s" % (name, val)
  print
  return sys.stdout.write
