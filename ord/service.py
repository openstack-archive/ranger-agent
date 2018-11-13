#!/usr/bin/env python
#
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

import socket
import sys

from oslo_config import cfg
import oslo_i18n as i18n

from ord.common import utils
from ord.i18n import _
from ord.openstack.common import log


OPTS = [
    cfg.StrOpt('host',
               default=socket.gethostname(),
               help='Name of this node, which must be valid in an AMQP '
               'key. Can be an opaque identifier. For ZeroMQ only, must '
               'be a valid host name, FQDN, or IP address.'),
]
cfg.CONF.register_opts(OPTS)


LOG = log.getLogger(__name__)


class WorkerException(Exception):
    """Exception for errors relating to service workers."""


def get_workers(name):
    workers = (cfg.CONF.get('%s_workers' % name) or
               utils.cpu_count())
    if workers and workers < 1:
        msg = (_("%(worker_name)s value of %(workers)s is invalid, "
                 "must be greater than 0") %
               {'worker_name': '%s_workers' % name, 'workers': str(workers)})
        raise WorkerException(msg)
    return workers


def prepare_service(argv=None):
    i18n.enable_lazy()
    log_levels = (cfg.CONF.default_log_levels +
                  ['stevedore=INFO'])
    cfg.set_defaults(log.log_opts,
                     default_log_levels=log_levels)
    if argv is None:
        argv = sys.argv
    cfg.CONF(argv[1:], project='ranger-agent', validate_default_values=True)
    log.setup('ranger')
    # messaging.setup()
