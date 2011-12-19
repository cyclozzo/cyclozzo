# -*- coding: utf-8 -*-
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
"""XMPP service API stub using ejabberd."""

import cyclozzo.apps.api.apiproxy_stub
import cyclozzo.apps.api.xmpp.xmpp_service_pb
import logging
import os
import xmpp

NO_ERROR = (cyclozzo.apps.api.xmpp.xmpp_service_pb.
            XmppMessageResponse.NO_ERROR)


class XmppServiceStub(cyclozzo.apps.api.apiproxy_stub.APIProxyStub):
    """XMPP service stub."""

    def __init__(self, log=logging.info, host='localhost', service_name='xmpp'):
        """Initializer.

        Args:
            log: A logger, used for dependency injection.
            host: Hostname of the XMPP service.
            service_name: Service name expected for all calls.
        """
        super(XmppServiceStub, self).__init__(service_name)
        self.log = log
        self.host = host

    def do_action(self, action, request):
        """Establishes the xmpp connection and makes an action.

        Args:
            action: A callable with client as first argument.
            request: The request.
        """
        jid = xmpp.protocol.JID(self._GetFrom(request.from_jid()))
        client = xmpp.Client(jid.getDomain(), debug=[])
        client.connect()
        node = jid.getNode()
        client.auth(node, node)
        result = action(client)
        client.disconnect()
        return result

    def _Dynamic_GetPresence(self, request, response):
        """Implementation of XmppService::GetPresence.

        Returns online.

        Args:
            request: A PresenceRequest.
            response: A PresenceResponse.
        """
        response.set_is_available(True)

    def _Dynamic_SendMessage(self, request, response):
        """Implementation of XmppService::SendMessage.

        Args:
            request: An XmppMessageRequest.
            response: An XmppMessageResponse .
        """
        def action(client):
            for to_jid in request.jid_list():
                client.send(xmpp.protocol.Message(to_jid, request.body()))
                response.add_status(NO_ERROR)

        self.do_action(action, request)

    def _Dynamic_SendInvite(self, request, response):
        """Implementation of XmppService::SendInvite.

        Args:
            request: An XmppInviteRequest.
            response: An XmppInviteResponse .
        """
        def action(client):
            roster = client.getRoster()
            roster.Subscribe(request.jid())

        self.do_action(action, request)

    def _Dynamic_SendPresence(self, request, response):
        """Implementation of XmppService::SendPresence.

        Args:
            request: An XmppSendPresenceRequest.
            response: An XmppSendPresenceResponse .
        """
        def action(client):
            client.sendPresence(request.jid())

        self.do_action(action, request)

    def _GetFrom(self, requested):
        """Validates that the from JID is valid.

        Args:
            requested: The requested from JID.

        Returns:
            string, The from JID.

        Raises:
            xmpp.InvalidJidError if the requested JID is invalid.
        """

        appid = os.environ['APPLICATION_ID']

        return '%s@%s' % (appid, self.host)
