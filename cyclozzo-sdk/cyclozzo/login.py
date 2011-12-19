#!/usr/bin/env python
"""Helper Handlers for logins/logout in the application server.

This Handler has these parameters:

	continue: URL to redirect to after a login or logout has completed.
	email: Email address to set for the client.
	admin: If 'True', the client should be logged in as an admin.
	action: What action to take ('Login' or 'Logout').

To view the current user information and a form for logging in and out,
supply no parameters.

@author: Sreejith K
Created on: 7th April 2010
"""

import Cookie
import os
import sys
import urllib
import logging
from hashlib import md5

import tornado
import tornado.web
from cyclozzo.runtime.lib.api import Client, ClientException
from cyclozzo.sdk.app import get_yaml

import cgi
import urlparse
import cgitb

from openid.consumer import consumer
from openid.oidutil import appendArgs
from openid.cryptutil import randomString
from openid.extensions import pape, sreg

CONTINUE_PARAM = 'continue'
LOGIN_PARAM = 'login'
ADMIN_PARAM = 'admin'
ACTION_PARAM = 'action'
PASSWORD_PARAM = 'password'
OPENID_PARAM = 'openid.mode'

LOGOUT_ACTION = 'Logout'
LOGIN_ACTION = 'Login'

LOGOUT_PARAM = 'action=%s' % LOGOUT_ACTION

COOKIE_NAME = 'appserver_login'

log = logging.getLogger(__name__)


# Used with an OpenID provider affiliate program.
OPENID_PROVIDER_NAME = 'MyOpenID'
OPENID_PROVIDER_URL ='https://www.myopenid.com/affiliate_signup?affiliate_id=39'


def quoteattr(s):
	qs = cgi.escape(s, 1)
	return '"%s"' % (qs,)

class CyclozzoAppSession(object):
	"""
	This is the BORG design pattern. It makes
	all instances of this class share the same state
	by reinitializing its __dict__ with shared class member
	"""
	__shared_state = {}
	
	def __init__(self):
		self.__dict__ = self.__shared_state
		self.cookies = {}
	
	def get_cookie(self, name):
		return self.cookies.get(name, None)
	
	def set_cookie(self, name, value):
		self.cookies[name] = value
	
	def clear_cookie(self, name):
		del self.cookies[name]

class OpenIDRequestHandler(tornado.web.RequestHandler):
	"""Request handler that knows how to verify an OpenID identity."""
	SESSION_COOKIE_NAME = 'pyoidconsexsid'

	session = None

	def getConsumer(self):
		return consumer.Consumer(self.getSession(), None)

	def getSession(self):
		"""Return the existing session or a new session"""
		if self.session is not None:
			return self.session

		# Get value of cookie header that was sent
		sid = self.get_cookie(self.SESSION_COOKIE_NAME, None)
		log.debug('\t\t --- session id: %s' %sid)
		if not sid:
			sid = randomString(16, '0123456789abcdef')

		self.set_cookie(self.SESSION_COOKIE_NAME, sid)
		session = {}
		session['id'] = sid
		self.session = session
		return session

	def setSessionCookie(self, id):
		sid = CreateCookieData(id, False)
		self.set_cookie(COOKIE_NAME, sid)

	def clearSessionCookie(self):
		log.debug('\t\t --- Clearing session cookie %s' %COOKIE_NAME)
		self.clear_cookie(COOKIE_NAME)

	def head(self):
		self._HandleRequest()

	def get(self):
		self._HandleRequest()

	def post(self):
		self._HandleRequest()

	def delete(self):
		self._HandleRequest()

	def put(self):
		self._HandleRequest()

	def _HandleRequest(self):
		"""Dispatching logic. There are three paths defined:

		/ - Display an empty form asking for an identity URL to
              verify
		/verify - Handle form submission, initiating OpenID verification
		/process - Handle a redirect from an OpenID server

		Any other path gets a 404 response. This function also parses
		the query parameters.

		If an exception occurs in this function, a traceback is
		written to the requesting browser.
		"""
		try:
			if self.get_argument(ACTION_PARAM, '') == LOGOUT_ACTION:
				self.clearSessionCookie()
				return self.redirect('/')
			log.debug('\t\t --- cookie: %s' %self.get_cookie(COOKIE_NAME, None))
			log.debug('\t\t --- cookie from header: %s' %self.request.headers.get('Cookie', None))
			self.base_url = ('http://%s' %self.request.host)
			self.login_url = urlparse.urljoin(self.base_url, '/_ah/login_required/')
			self.parsed_uri = urlparse.urlparse(self.request.full_url())
			self.query = {}
			for k, v in cgi.parse_qsl(self.parsed_uri[4]):
				self.query[k] = v.decode('utf-8')

			path = self.parsed_uri[2]
			if path == '/_ah/login_required':
				self.render_page()
			elif path == '/_ah/login_required/verify':
				self.doVerify()
			elif path == '/_ah/login_required/process':
				self.doProcess()
			elif path == '/_ah/login_required/affiliate':
				self.doAffiliate()
			else:
				self.notFound()

		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			self.set_status(500)
			self.set_header('Content-type', 'text/html')
			self.setSessionCookie('')
			self.write(cgitb.html(sys.exc_info(), context=10))
			self.finish()

	def doVerify(self):
		"""Process the form submission, initating OpenID verification.
		"""

		# First, make sure that the user entered something
		openid_url = self.query.get('openid_identifier')
		if not openid_url:
			self.render_page('Enter an OpenID Identifier to verify.',
							css_class='error', form_contents=openid_url)
			return

		immediate = 'immediate' in self.query
		use_sreg = 'use_sreg' in self.query
		use_pape = 'use_pape' in self.query
		#use_stateless = 'use_stateless' in self.query

		oidconsumer = self.getConsumer()
		try:
			request = oidconsumer.begin(openid_url)
		except consumer.DiscoveryFailure, exc:
			fetch_error_string = 'Error in discovery: %s' % (
								cgi.escape(str(exc[0])))
			self.render_page(fetch_error_string,
							css_class='error',
							form_contents=openid_url)
		else:
			if request is None:
				msg = 'No OpenID services found for <code>%s</code>' % (
							cgi.escape(openid_url),)
				self.render_page(msg, css_class='error', form_contents=openid_url)
			else:
				# Then, ask the library to begin the authorization.
				# Here we find out the identity server that will verify the
				# user's identity, and get a token that allows us to
				# communicate securely with the identity server.
				if use_sreg:
					self.requestRegistrationData(request)

				if use_pape:
					self.requestPAPEDetails(request)

				trust_root = self.base_url
				return_to = self.buildURL('process')
				if request.shouldSendRedirect():
					redirect_url = request.redirectURL(
								trust_root, return_to, immediate=immediate)
					self.set_status(302)
					self.set_header('Location', redirect_url)
				else:
					form_html = request.htmlMarkup(
						trust_root, return_to,
						form_tag_attrs={'id':'openid_message'},
						immediate=immediate)

					self.write(form_html)

	def requestRegistrationData(self, request):
		sreg_request = sreg.SRegRequest(
				required=['nickname'], optional=['fullname', 'email'])
		request.addExtension(sreg_request)

	def requestPAPEDetails(self, request):
		pape_request = pape.Request([pape.AUTH_PHISHING_RESISTANT])
		request.addExtension(pape_request)

	def doProcess(self):
		"""Handle the redirect from the OpenID server.
		"""
		oidconsumer = self.getConsumer()

		# Ask the library to check the response that the server sent
		# us.  Status is a code indicating the response type. info is
		# either None or a string containing more information about
		# the return type.
		url = 'http://'+ self.request.headers.get('Host') + self.request.path
		info = oidconsumer.complete(self.query, url)

		sreg_resp = None
		pape_resp = None
		css_class = 'error'
		display_identifier = info.getDisplayIdentifier()

		if info.status == consumer.FAILURE and display_identifier:
			# In the case of failure, if info is non-None, it is the
			# URL that we were verifying. We include it in the error
			# message to help the user figure out what happened.
			fmt = "Verification of %s failed: %s"
			message = fmt % (cgi.escape(display_identifier),
							info.message)
		elif info.status == consumer.SUCCESS:
			# Success means that the transaction completed without
			# error. If info is None, it means that the user cancelled
			# the verification.
			css_class = 'alert'

			# This is a successful verification attempt. If this
			# was a real application, we would do our login,
			# comment posting, etc. here.
			fmt = "You have successfully verified %s as your identity."
			message = fmt % (cgi.escape(display_identifier),)
			sreg_resp = sreg.SRegResponse.fromSuccessResponse(info)
			pape_resp = pape.Response.fromSuccessResponse(info)
			if info.endpoint.canonicalID:
				# You should authorize i-name users by their canonicalID,
				# rather than their more human-friendly identifiers.  That
				# way their account with you is not compromised if their
				# i-name registration expires and is bought by someone else.
				message += ("  This is an i-name, and its persistent ID is %s"
						% (cgi.escape(info.endpoint.canonicalID),))
			self.setSessionCookie( info.getDisplayIdentifier() )
		elif info.status == consumer.CANCEL:
			# cancelled
			message = 'Verification cancelled'
		elif info.status == consumer.SETUP_NEEDED:
			if info.setup_url:
				message = '<a href=%s>Setup needed</a>' % (
						quoteattr(info.setup_url),)
			else:
				# This means auth didn't succeed, but you're welcome to try
				# non-immediate mode.
				message = 'Setup needed'
		else:
			# Either we don't understand the code or there is no
			# openid_url included with the error. Give a generic
			# failure message. The library should supply debug
			# information in a log.
			message = 'Verification failed.'

		self.render_page(message, css_class, display_identifier,
						sreg_data=sreg_resp, pape_data=pape_resp)

	def doAffiliate(self):
		"""Direct the user sign up with an affiliate OpenID provider."""
		sreg_req = sreg.SRegRequest(['nickname'], ['fullname', 'email'])
		href = sreg_req.toMessage().toURL(OPENID_PROVIDER_URL)

		message = """Get an OpenID at <a href=%s>%s</a>""" % (
						quoteattr(href), OPENID_PROVIDER_NAME)
		self.render_page(message)

	def renderSREG(self, sreg_data):
		if not sreg_data:
			self.write(
					'<div class="alert">No registration data was returned</div>')
		else:
			sreg_list = sreg_data.items()
			sreg_list.sort()
			self.write(
					'<h2>Registration Data</h2>'
					'<table class="sreg">'
					'<thead><tr><th>Field</th><th>Value</th></tr></thead>'
					'<tbody>')

			odd = ' class="odd"'
			for k, v in sreg_list:
				field_name = sreg.data_fields.get(k, k)
				value = cgi.escape(v.encode('UTF-8'))
				self.write(
						'<tr%s><td>%s</td><td>%s</td></tr>' % (odd, field_name, value))
				if odd:
					odd = ''
				else:
					odd = ' class="odd"'

			self.write('</tbody></table>')

	def renderPAPE(self, pape_data):
		if not pape_data:
			self.write(
					'<div class="alert">No PAPE data was returned</div>')
		else:
			self.write('<div class="alert">Effective Auth Policies<ul>')

			for policy_uri in pape_data.auth_policies:
				self.write('<li><tt>%s</tt></li>' % (cgi.escape(policy_uri),))

			if not pape_data.auth_policies:
				self.write('<li>No policies were applied.</li>')

			self.write('</ul></div>')

	def buildURL(self, action, **query):
		"""Build a URL relative to the server base_url, with the given
		query parameters added."""
		base = urlparse.urljoin(self.login_url, action)
		return appendArgs(base, query)

	def notFound(self):
		"""Render a page with a 404 return code and a message."""
		fmt = 'The path <q>%s</q> was not understood by this server.'
		msg = fmt % (self.request.path,)
		openid_url = self.query.get('openid_identifier')
		self.render_page(msg, 'error', openid_url, status=404)

	def render_page(self, message=None, css_class='alert', form_contents=None,
				status=200, title="Python OpenID Consumer Example",
				sreg_data=None, pape_data=None):
		"""Render a page."""
		self.set_status(status)
		self.pageHeader(title)
		if message:
			self.write("<div class='%s'>" % (css_class,))
			self.write(message)
			self.write("</div>")

		if sreg_data is not None:
			self.renderSREG(sreg_data)

		if pape_data is not None:
			self.renderPAPE(pape_data)

		self.pageFooter(form_contents)
		self.flush()

	def pageHeader(self, title):
		"""Render the page header"""
		self.set_header('Content-type', 'text/html; charset=UTF-8')
		self.write('''\
<html>
  <head><title>%s</title></head>
  <style type="text/css">
      * {
        font-family: verdana,sans-serif;
      }
      body {
        width: 50em;
        margin: 1em;
      }
      div {
        padding: .5em;
      }
      tr.odd td {
        background-color: #dddddd;
      }
      table.sreg {
        border: 1px solid black;
        border-collapse: collapse;
      }
      table.sreg th {
        border-bottom: 1px solid black;
      }
      table.sreg td, table.sreg th {
        padding: 0.5em;
        text-align: left;
      }
      table {
        margin: 0;
        padding: 0;
      }
      .alert {
        border: 1px solid #e7dc2b;
        background: #fff888;
      }
      .error {
        border: 1px solid #ff0000;
        background: #ffaaaa;
      }
      #verify-form {
        border: 1px solid #777777;
        background: #dddddd;
        margin-top: 1em;
        padding-bottom: 0em;
      }
  </style>
  <body>
    <h1>%s</h1>
    <p>
      This example consumer uses the <a href=
      "http://github.com/openid/python-openid" >Python
      OpenID</a> library. It just verifies that the identifier that you enter
      is your identifier.
    </p>
''' % (title, title))

	def pageFooter(self, form_contents):
		"""Render the page footer"""
		if not form_contents:
			form_contents = ''

		self.write('''
    <div id="verify-form">
      <form method="get" accept-charset="UTF-8" action=%s>
        Identifier:
        <input type="text" name="openid_identifier" value=%s />
        <input type="submit" value="Verify" /><br />
        <input type="checkbox" name="immediate" id="immediate" /><label for="immediate">Use immediate mode</label>
        <input type="checkbox" name="use_sreg" id="use_sreg" /><label for="use_sreg">Request registration data</label>
        <input type="checkbox" name="use_pape" id="use_pape" /><label for="use_pape">Request phishing-resistent auth policy (PAPE)</label>
        <input type="checkbox" name="use_stateless" id="use_stateless" /><label for="use_stateless">Use stateless mode</label>
      </form>
    </div>
  </body>
</html>
''' % (quoteattr(self.buildURL('verify')), quoteattr(form_contents)))


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


LOGIN_TEMPLATE = """<html>
<head>
	<title>Login</title>
</head>
<body>

<form method='get' action='%(login_url)s'
		style='text-align:center; font: 13px sans-serif'>
	<div style='width: 20em; margin: 1em auto;
				text-align:left;
				padding: 0 2em 1.25em 2em;
				background-color: #d6e9f8;
				border: 2px solid #67a7e3'>
	<div style='text-align:center'>Cyclozzo Login</div>
	<h3>%(login_message)s</h3>
	<p style='padding: 0; margin: 0'>
		<label for='login' style="width: 3em">Login:</label>
		<input name='login' type='text' value='%(login)s' id='login'/>
	</p>
	<p style='padding: 0; margin: 0'>
		<label for='password' style="width: 3em">Password:</label>
		<input name='password' type='password' id='password'/>
	</p>
	<p style='margin-left: 3em'>
		<input name='action' value='Login' type='submit'
			id='submit-login' />
	<input name='action' value='Logout' type='submit'
			id='submit-logout' />
	</p>
	</div>
	

		<p> %(message)s </p>

	
	<input name='continue' type='hidden' value='%(continue_url)s'/>
</form>

</body>
</html>
"""

def CreateLoginRequestHandler(proxy_class, config):
	
	master = proxy_class(address=config.master_address, 
						port = config.master_port)
	resp = master.connect()
	
	class LoginRequestHandler(tornado.web.RequestHandler):
		def setSessionCookie(self, id, is_admin=False):
			sid = CreateCookieData(id, is_admin)
			self.set_cookie(COOKIE_NAME, sid)
	
		def clearSessionCookie(self):
			log.debug('\t\t --- Clearing session cookie %s' %COOKIE_NAME)
			self.clear_cookie(COOKIE_NAME)
	
		def getSessionCookie(self):
			return self.get_cookie(COOKIE_NAME, None)
	
		def head(self):
			self._HandleRequest()
	
		def get(self):
			self._HandleRequest()
	
		def post(self):
			self._HandleRequest()
	
		def delete(self):
			self._HandleRequest()
	
		def put(self):
			self._HandleRequest()
	
		def _HandleRequest(self):
#			try:
			login_url = self.request.path
			authenticated = False
			login_message = 'Not logged in'
			cookie = self.getSessionCookie()
			if cookie:
				email, admin, user_id = cookie.split(':')
				admin = (admin == 'True')
				log.debug('auth is %s ; %s ; %s' %(email, admin, user_id))
				authenticated = True
				login_message = 'Logged in as %s' %email
			
			set_email = ''
			msg = ''
	
			action = self.get_argument(ACTION_PARAM, None)
			continue_url = self.get_argument(CONTINUE_PARAM, '')
			if action == LOGOUT_ACTION:
				self.clearSessionCookie()
			elif action == LOGIN_ACTION:	
				login_name = self.get_argument(LOGIN_PARAM, '')
				password = self.get_argument(PASSWORD_PARAM, '')
				password_hash = md5(password).hexdigest()

				args = {'user_id': login_name,
						'password_hash': password_hash,
						'app_id': get_yaml().application
					}
				
				log.debug('Authenticating with master')
				authenticated, set_admin, set_email, msg = \
								master.authenticate(resp.token, args)
				if authenticated:
					self.setSessionCookie(set_email, set_admin)
			
			if authenticated and continue_url:
				return self.redirect(continue_url)
				
			continue_url = continue_url or login_url
			template_dict = {
							'login': set_email or 'admin',
							'login_message': login_message,
							'login_url': login_url,
							'continue_url': continue_url,
							'message': msg
							}
			log.debug('Auth message: %s' %msg)
			self.write( LOGIN_TEMPLATE % template_dict )
	
	return LoginRequestHandler
