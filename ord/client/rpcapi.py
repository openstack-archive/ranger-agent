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

LOG = logging.getLogger(__name__)


class RpcAPI(object):

    def __init__(self):
        super(RpcAPI, self).__init__()

        self.target = messaging.Target(topic='ord-notifier-q')
        self.transport = messaging.get_rpc_transport(cfg.CONF)
        self._client = messaging.RPCClient(self.transport, self.target)

    def invoke_notifier_rpc(self, ctxt, payload):
        try:
            cctxt = self._client.prepare(version='1.0')
            cctxt.cast(ctxt=ctxt,
                       method='invoke_notifier_rpc',
                       payload=payload)

        except messaging.MessageDeliveryFailure:
            LOG.error("Fail to deliver message")
