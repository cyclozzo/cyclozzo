# -*- coding: utf-8 -*-
"""
    tipfy.auth.openid
    ~~~~~~~~~~~~~~~~~

    Implementation of OpenId authentication scheme.

    Ported from `tornado.auth`_.

    :copyright: 2009 Facebook.
    :copyright: 2011 tipfy.org.
    :license: Apache License Version 2.0, see LICENSE.txt for more details.
"""

from __future__ import absolute_import
import logging
import urllib
import urlparse

from cyclozzo.apps.api import urlfetch


class OpenIdMixin(object):
    """A :class:`tipfy.RequestHandler` mixin that implements OpenID
    authentication with Attribute Exchange.
    """
    #: OpenId provider endpoint. For example,
    #: 'https://www.google.com/accounts/o8/ud'
    _OPENID_ENDPOINT = None

    def authenticate_redirect(self, callback_uri=None, ax_attrs=None,
        openid_endpoint=None):
        """Returns the authentication URL for this service.

        After authentication, the service will redirect back to the given
        callback URI.

        We request the given attributes for the authenticated user by
        default (name, email, language, and username). If you don't need
        all those attributes for your app, you can request fewer with
        the ax_attrs keyword argument.

        :param callback_uri:
            The URL to redirect to after authentication.
        :param ax_attrs:
            List of Attribute Exchange attributes to be fetched.
        :param openid_endpoint:
            OpenId provider endpoint. If not set, uses the value set in
            :attr:`_OPENID_ENDPOINT`.
        :returns:
            None.
        """
        callback_uri = callback_uri or self.request.path
        ax_attrs = ax_attrs or ('name', 'email', 'language', 'username')
        openid_endpoint = openid_endpoint or self._OPENID_ENDPOINT
        args = self._openid_args(callback_uri, ax_attrs=ax_attrs)
        return self.redirect(make_full_url(openid_endpoint, args))

    def get_authenticated_user(self, callback, openid_endpoint=None):
        """Fetches the authenticated user data upon redirect.

        This method should be called by the handler that receives the
        redirect from the authenticate_redirect() or authorize_redirect()
        methods.

        :param callback:
            A function that is called after the authentication attempt. It
            is called passing a dictionary with the requested user attributes
            or None if the authentication failed.
        :param openid_endpoint:
            OpenId provider endpoint. For example,
            'https://www.google.com/accounts/o8/ud'.
        :returns:
            The result from the callback function.
        """
        # Changed method to POST. See:
        # https://github.com/facebook/tornado/commit/e5bd0c066afee37609156d1ac465057a726afcd4

        # Verify the OpenID response via direct request to the OP
        url = openid_endpoint or self._OPENID_ENDPOINT
        logging.debug('Request Params: %s' %str(dir(self.request)))
        args_lists = {}
        for entry in self.request.query.split('&'):
            k, v = entry.split('=')
            if k in args_lists:
                args_lists[k].append(v)
            else:
                args_lists[k] = [v]

        logging.debug('--> %r' %args_lists.items())
        #args = dict((k, v[-1].encode('utf8')) for k, v in self.request.args.lists())
        args = dict((k, v[-1].encode('utf8')) for k, v in args_lists.items())
        args['openid.mode'] = u'check_authentication'

        try:
            response = urlfetch.fetch(url, deadline=10, method=urlfetch.POST,
                payload=urllib.urlencode(args))
            if response.status_code < 200 or response.status_code >= 300:
                logging.warning('Invalid OpenID response: %s',
                    response.content)
            else:
                return self._on_authentication_verified(callback, response)
        except urlfetch.DownloadError, e:
            logging.exception(e)

        return self._on_authentication_verified(callback, None)


    def _openid_args(self, callback_uri, ax_attrs=None, oauth_scope=None):
        """Builds and returns the OpenId arguments used in the authentication
        request.

        :param callback_uri:
            The URL to redirect to after authentication.
        :param ax_attrs:
            List of Attribute Exchange attributes to be fetched.
        :param oauth_scope:
        :returns:
            A dictionary of arguments for the authentication URL.
        """
        url = urlparse.urljoin(self.request.url, callback_uri)
        args = {
            'openid.ns': 'http://specs.openid.net/auth/2.0',
            'openid.claimed_id':
                'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.identity':
                'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.return_to': url,
            'openid.realm': self.request.environ['wsgi.url_scheme'] + \
                '://' + self.request.host + '/',
            'openid.mode': 'checkid_setup',
        }
        if ax_attrs:
            args.update({
                'openid.ns.ax': 'http://openid.net/srv/ax/1.0',
                'openid.ax.mode': 'fetch_request',
            })
            ax_attrs = set(ax_attrs)
            required = []
            if 'name' in ax_attrs:
                ax_attrs -= set(['name', 'firstname', 'fullname', 'lastname'])
                required += ['firstname', 'fullname', 'lastname']
                args.update({
                    'openid.ax.type.firstname':
                        'http://axschema.org/namePerson/first',
                    'openid.ax.type.fullname':
                        'http://axschema.org/namePerson',
                    'openid.ax.type.lastname':
                        'http://axschema.org/namePerson/last',
                })

            known_attrs = {
                'email': 'http://axschema.org/contact/email',
                'language': 'http://axschema.org/pref/language',
                'username': 'http://axschema.org/namePerson/friendly',
            }

            for name in ax_attrs:
                args['openid.ax.type.' + name] = known_attrs[name]
                required.append(name)

            args['openid.ax.required'] = ','.join(required)

        if oauth_scope:
            args.update({
                'openid.ns.oauth':
                    'http://specs.openid.net/extensions/oauth/1.0',
                'openid.oauth.consumer': self.request.host.split(':')[0],
                'openid.oauth.scope': oauth_scope,
            })

        return args

    def _on_authentication_verified(self, callback, response):
        """Called after the authentication attempt. It calls the callback
        function set when the authentication process started, passing a
        dictionary of user data if the authentication was successful or
        None if it failed.

        :param callback:
            A function that is called after the authentication attempt. It
            is called passing a dictionary with the requested user attributes
            or None if the authentication failed.
        :param response:
            The response returned from the urlfetch call after the
            authentication attempt.
        :returns:
            The result from the callback function.
        """
        if not response:
            logging.warning('Missing OpenID response.')
            return callback(None)
        elif response.status_code < 200 or response.status_code >= 300:
            logging.warning('Invalid OpenID response (%d): %s',
                response.status_code, response.content)
            return callback(None)

        # Make sure we got back at least an email from Attribute Exchange.
        ax_ns = None
        for name, values in self.request.args.iterlists():
            if name.startswith('openid.ns.') and \
                values[-1] == u'http://openid.net/srv/ax/1.0':
                ax_ns = name[10:]
                break

        _ax_args = [
            ('email',      'http://axschema.org/contact/email'),
            ('name',       'http://axschema.org/namePerson'),
            ('first_name', 'http://axschema.org/namePerson/first'),
            ('last_name',  'http://axschema.org/namePerson/last'),
            ('username',   'http://axschema.org/namePerson/friendly'),
            ('locale',     'http://axschema.org/pref/language'),
        ]

        user = {}
        name_parts = []
        
        openid_signed_params = self.request.args.get("openid.signed", u'').split(',')
        
        for name, uri in _ax_args:
            value = self._get_ax_arg(uri, ax_ns, openid_signed_params)
            if value:
                user[name] = value
                if name in ('first_name', 'last_name'):
                    name_parts.append(value)

        if not user.get('name'):
            if name_parts:
                user['name'] = u' '.join(name_parts)
            elif user.get('email'):
                user['name'] = user.get('email').split('@', 1)[0]

        # get the claimed_id
        user['claimed_id'] = self.request.args.get('openid.claimed_id', u'')

        return callback(user)

    def _get_ax_arg(self, uri, ax_ns, openid_signed_params):
        """Returns an Attribute Exchange value from request.

        :param uri:
            Attribute Exchange URI.
        :param ax_ns:
            Attribute Exchange namespace.
        :returns:
            The Attribute Exchange value, if found in request.
        """
        if not ax_ns:
            return u''

        prefix = 'openid.' + ax_ns + '.type.'
        ax_name = None
        for name, values in self.request.args.iterlists():
            if not name[len("openid."):] in openid_signed_params:
                continue
            if values[-1] == uri and name.startswith(prefix):
                part = name[len(prefix):]
                ax_name = 'openid.' + ax_ns + '.value.' + part
                break

        if not ax_name:
            return u''
        
        if not ax_name[len("openid."):] in openid_signed_params: 
            return u''

        return self.request.args.get(ax_name, u'')


def make_full_url(base, args):
    if "?" in base:
        delimiter = "&"
    else:
        delimiter = "?"

    return base + delimiter + urllib.urlencode(args)
