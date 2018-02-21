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

from ord.engine.engine import Engine
from ord.engine.engine import QueueHandler
from oslo_config import cfg
import oslo_messaging as messaging


def start():
    engine = Engine()

    # start Notify message listener
    transport = messaging.get_rpc_transport(cfg.CONF)

    target = messaging.Target(topic='ord-notifier-q', server=cfg.CONF.host)

    endpoints = [QueueHandler(engine)]

    server = messaging.get_rpc_server(transport,
                                      target,
                                      endpoints,
                                      executor='blocking')

    try:
        server.start()
        server.wait()
    except KeyboardInterrupt:
        # Add termination handling here
        pass
