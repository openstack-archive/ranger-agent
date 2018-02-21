# Copyright (c) 2012 OpenStack Foundation
# All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import logging
from oslo_config import cfg
import oslo_messaging as messaging

from ord.common.exceptions import RPCInitializationException

LOG = logging.getLogger(__name__)


class RpcEngine(object):

    def __init__(self):
        super(RpcEngine, self).__init__()
        try:
            self.target = messaging.Target(topic='ord-listener-q')
            self.transport = messaging.get_notification_transport(cfg.CONF)
            self._client = messaging.RPCClient(self.transport, self.target)
        except Exception as exception:
            LOG.critical(
                "Unexpected error while initializing clients %s" % exception)
            raise RPCInitializationException(exception.message)

    def invoke_listener_rpc(self, ctxt, payload):
        LOG.debug("invoke_listener_rpc is invoked")
        try:
            cctxt = self._client.prepare(version='1.0')
            cctxt.cast(ctxt=ctxt,
                       method='invoke_listener_rpc',
                       payload=payload)

        except messaging.MessageDeliveryFailure:
            LOG.error("Fail to deliver message")
