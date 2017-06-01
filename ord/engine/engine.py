#  Copyright 2016 ATT
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

from multiprocessing import Process
import os
from oslo_config import cfg

from ord.client import rpcengine
from ord.engine.workerfactory import WorkerFactory
from ord.openstack.common import log as logging


OPTS = [
    cfg.StrOpt('local_repo',
               default='aic-orm-resources-labs',
               help='local repo from where the'
                    'template yaml can be accessed from'),
    cfg.StrOpt('region',
               default='local',
               help='Region'),
]
cfg.CONF.register_opts(OPTS)
CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class QueueHandler(object):

    def __init__(self, engine):
        super(QueueHandler, self).__init__()
        self._engine = engine
        self._rpcengine = rpcengine.RpcEngine()
        self.factory = WorkerFactory()

    def invoke_notifier_rpc(self, ctxt, payload):

        LOG.debug("\n----- message from API -----")
        LOG.debug("\n Payload: %s \nctxt: %s "
                  % (str(payload), str(ctxt)))
        LOG.debug("\n-------------------------------\n")

        d = eval(payload)
        template_type = d["template_type"]
        resource_name = d["resource_name"]
        resource_type = d["resource_type"]
        operation = d["resource_operation"]
        template_status_id = d["template_status_id"]
        region = d["region"]
        stack_name = resource_name[:resource_name.index(".")]
        path_to_tempate = os.path.join(region, template_type,
                                       resource_type, resource_name)
        worker = self.factory.getWorker(operation, path_to_tempate,
                                        stack_name, template_status_id,
                                        resource_type, template_type)
        self.factory.execute(worker, operation)


class Engine(object):
    """This class provides functionality which allows to interact the
    basic ORD clients.
    """

    def __init__(self):
        """Initialize an engine.

        :return: instance of the engine class
        """
        super(Engine, self).__init__()
        # FIXME self.factory = WorkerFactory()

    def _execute(self):
        """Start the process activity."""
        LOG.info("Waiting for a message...")

    def start(self):
        process = Process(target=self._execute)
        try:
            """Start the engine."""
            LOG.info("Starting the engine... (Press CTRL+C to quit)")
            process.start()
            process.join()
        except KeyboardInterrupt:
            process.terminate()
