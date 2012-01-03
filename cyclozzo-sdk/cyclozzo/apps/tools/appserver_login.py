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
"""Helper CGI for logins/logout in the development application server.

This CGI has these parameters:

  continue: URL to redirect to after a login or logout has completed.
  email: Email address to set for the client.
  admin: If 'True', the client should be logged in as an admin.
  action: What action to take ('Login' or 'Logout').

To view the current user information and a form for logging in and out,
supply no parameters.
"""


import cgi
import Cookie
from hashlib import md5
import os
import sys
import urllib
import logging


import tornado.web
import tornado.auth
import tornado.wsgi


CONTINUE_PARAM = 'continue'
LOGIN_PARAM = 'login'
ADMIN_PARAM = 'admin'
ACTION_PARAM = 'action'
PASSWD_PARAM = 'password'

LOGOUT_ACTION = 'Logout'
LOGIN_ACTION = 'Login'

LOGOUT_PARAM = 'action=%s' % LOGOUT_ACTION

COOKIE_NAME = 'dev_appserver_login'


def LoginRedirect(login_url,
                  hostname,
                  port,
                  relative_url,
                  outfile):
    """Writes a login redirection URL to a user.

    Args:
        login_url: Relative URL which should be used for handling user logins.
        hostname: Name of the host on which the webserver is running.
        port: Port on which the webserver is running.
        relative_url: String containing the URL accessed.
        outfile: File-like object to which the response should be written.
    """
    dest_url = "http://%s:%s%s" % (hostname, port, relative_url)
    redirect_url = 'http://%s:%s%s?%s=%s' % (hostname,
                                             port,
                                             login_url,
                                             CONTINUE_PARAM,
                                             urllib.quote(dest_url))
    outfile.write('Status: 302 Requires login\r\n')
    outfile.write('Location: %s\r\n\r\n' % redirect_url)


def GetUserInfo(http_cookie, cookie_name=COOKIE_NAME):
    """Get the requestor's user info from the HTTP cookie in the CGI environment.

    Args:
        http_cookie: Value of the HTTP_COOKIE environment variable.
        cookie_name: Name of the cookie that stores the user info.

    Returns:
        Tuple (email, admin) where:
            email: The user's email address, if any.
            admin: True if the user is an admin; False otherwise.
    """
    cookie = Cookie.SimpleCookie(http_cookie)

    cookie_value = ''
    if cookie_name in cookie:
        cookie_value = cookie[cookie_name].value

    email, admin, user_id = (cookie_value.split(':') + ['', '', ''])[:3]
    return email, (admin == 'True'), user_id


def CreateCookieData(email, admin):
    """Creates cookie payload data.

      Args:
        email, admin: Parameters to incorporate into the cookie.

      Returns:
        String containing the cookie payload.
    """
    admin_string = 'False'
    if admin:
        admin_string = 'True'
    if email:
        user_id_digest = md5(email.lower()).digest()
        user_id = '1' + ''.join(['%02d' % ord(x) for x in user_id_digest])[:20]
    else:
        user_id = ''
    return '%s:%s:%s' % (email, admin_string, user_id)


def ClearUserInfoCookie(cookie_name=COOKIE_NAME):
    """Clears the user info cookie from the requestor, logging them out.

    Args:
        cookie_name: Name of the cookie that stores the user info.

    Returns:
        'Set-Cookie' header for clearing the user info of the requestor.
    """
    set_cookie = Cookie.SimpleCookie()
    set_cookie[cookie_name] = ''
    set_cookie[cookie_name]['path'] = '/'
    set_cookie[cookie_name]['max-age'] = '0'
    return '%s\r\n' % set_cookie


def GetOpenIDLoginHandler(admin_name):
    
    admin_name = admin_name

    class OpenIDLoginHandler(tornado.web.RequestHandler, tornado.auth.OpenIdMixin):
        
        _OPENID_ENDPOINT = 'https://www.google.com/accounts/o8/ud'
    
        @tornado.web.asynchronous
        def get(self):
            if self.get_argument('action', None) == 'logout':
                self.clear_cookie(COOKIE_NAME, path='/')
                return self.redirect('/')
            if self.get_argument('openid.mode', None):
                self.get_authenticated_user(self.async_callback(self._on_auth))
                return
            self.authenticate_redirect()
    
        def _on_auth(self, user):
            """This function was set as callback in get() to be executed after an
            authentication attempt. If the authentication is valid, user will be
            dictionary with user attributes, if the authentication is not valid
            it will be None.
    
            :param user:
                A dictionary with user attributes if the authentication is valid,
                or None.
            :return:
                A response object.
            """
            if not user:
                # Authentication failed.
                raise tornado.web.HTTPError(500, 'Google auth failed')
    
            # For this example, we just display the user atttributes. You should
            # use this information to set a user session to keep the user logged
            # in, then redirect to original page where the user was before
            # requesting authentication.
            logging.debug('Authentication info: %s' %str(user))
            user_cookie = CreateCookieData(user['email'], (user['email'] == admin_name))
            logging.debug('User cookie: %s' %user_cookie)
            self.set_cookie(COOKIE_NAME, user_cookie, path='/')
            return self.redirect('/')

    return OpenIDLoginHandler

