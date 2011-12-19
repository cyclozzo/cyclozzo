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

"""Trivial implementation of the UserService."""


import os
import urllib
import urlparse
import logging
from cyclozzo.apps.api import apiproxy_stub
from cyclozzo.apps.api import user_service_pb
from cyclozzo.runtime.lib.config import get_yaml
import simplejson
from cyclozzo.apps.api import urlfetch

_DEFAULT_LOGIN_URL = 'https://www.google.com/accounts/Login?continue=%s'
_DEFAULT_LOGOUT_URL = 'https://www.google.com/accounts/Logout?continue=%s'

_OAUTH_CONSUMER_KEY = 'example.com'
_OAUTH_EMAIL = 'example@example.com'
_OAUTH_USER_ID = '0'
_OAUTH_AUTH_DOMAIN = 'gmail.com'


class UserServiceStub(apiproxy_stub.APIProxyStub):
  """Trivial implementation of the UserService."""

  def __init__(self,
               login_url=_DEFAULT_LOGIN_URL,
               logout_url=_DEFAULT_LOGOUT_URL,
               console_address='localhost',
               console_port=8080,
               service_name='user'):
    """Initializer.

    Args:
      login_url: String containing the URL to use for logging in.
      logout_url: String containing the URL to use for logging out.
      service_name: Service name expected for all calls.

    Note: Both the login_url and logout_url arguments must contain one format
    parameter, which will be replaced with the continuation URL where the user
    should be redirected after log-in or log-out has been completed.
    """
    super(UserServiceStub, self).__init__(service_name)
    self.__num_requests = 0
    self._login_url = login_url
    self._logout_url = logout_url
    self.console_address = console_address
    self.console_port = console_port

    os.environ['AUTH_DOMAIN'] = 'gmail.com'

  def num_requests(self):
    return self.__num_requests

  def _Dynamic_CreateLoginURL(self, request, response):
    """Trivial implementation of UserService.CreateLoginURL().

    Args:
      request: a CreateLoginURLRequest
      response: a CreateLoginURLResponse
    """
    self.__num_requests += 1
    response.set_login_url(
        self._login_url %
        urllib.quote(self._AddHostToContinueURL(request.destination_url())))

  def _Dynamic_CreateLogoutURL(self, request, response):
    """Trivial implementation of UserService.CreateLogoutURL().

    Args:
      request: a CreateLogoutURLRequest
      response: a CreateLogoutURLResponse
    """
    self.__num_requests += 1
    response.set_logout_url(
        self._logout_url %
        urllib.quote(self._AddHostToContinueURL(request.destination_url())))

  def _Dynamic_GetOAuthUser(self, unused_request, response):
    """Trivial implementation of UserService.GetOAuthUser().

    Args:
      unused_request: a GetOAuthUserRequest
      response: a GetOAuthUserResponse
    """
    self.__num_requests += 1
    response.set_email(_OAUTH_EMAIL)
    response.set_user_id(_OAUTH_USER_ID)
    response.set_auth_domain(_OAUTH_AUTH_DOMAIN)

  def _Dynamic_CheckOAuthSignature(self, unused_request, response):
    """Trivial implementation of UserService.CheckOAuthSignature().

    Args:
      unused_request: a CheckOAuthSignatureRequest
      response: a CheckOAuthSignatureResponse
    """
    self.__num_requests += 1
    response.set_oauth_consumer_key(_OAUTH_CONSUMER_KEY)

  def _AddHostToContinueURL(self, continue_url):
    """Adds the request host to the continue url if no host is specified.

    Args:
      continue_url: the URL which may or may not have a host specified

    Returns:
      string
    """
    (protocol, host, path, parameters, query, fragment) = urlparse.urlparse(continue_url, 'http')

    if host:
      return continue_url

    host = os.environ['SERVER_NAME']
    if os.environ['SERVER_PORT'] != '80':
      host = host + ":" + os.environ['SERVER_PORT']

    if path == '':
      path = '/'

    return urlparse.urlunparse(
      (protocol, host, path, parameters, query, fragment))

  def _Dynamic_Authenticate(self, req, resp):
    """Authenticate Cyclozzo User"""
    username, passwd_hash = req.get_auth_vars()
    args = {'user_id': username, 'password_hash': passwd_hash, 'app_id': get_yaml().application}
    logging.debug('authenticating with console at http://%s:%d' %(self.console_address, self.console_port))
    try:
      res = urlfetch.fetch('http://%s:%d/api/authenticate?%s' %(self.console_address, self.console_port, urllib.urlencode(args))).content
      authenticated, admin, email, msg = simplejson.loads(res)
    except Exception, ex:
      logging.error('Error authenticating user %s' %username)
      authenticated, email, admin, msg = False, '', False, 'Error authenticating user: %s' %str(ex)
    resp.set_auth_result(authenticated, email, admin, msg)
