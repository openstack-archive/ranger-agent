# Copyright 2016 ATT
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from ord.tests import base
from ord.engine.workerfactory import WorkerFactory
from ord.common.exceptions import WorkerThreadError


class TestWorkerFactory(base.BaseTestCase):

    def setUp(self):
        self.operation = 'create'
        self.path_to_tempate = 'test_path'
        self.stack_name = 'test_stack'
        self.template_status_id = '1'
        self.resource_type = 'image'
        self.template_type = 'hot'
        self.threadId = 123

        super(TestWorkerFactory, self).setUp()

        self.clients = mock.Mock()

        self.patch('ord.client.getrepo.TemplateRepoClient')\
            .return_value = self.clients
        self.patch('ord.client.heat.HeatClient').return_value = self.clients
        self.patch('ord.client.rpcengine.RpcEngine')\
            .return_value = self.clients

        self.worker = WorkerFactory()

    def test_getWorker(self):
        threadId = self.worker.getWorker(self.operation, self.path_to_tempate,
                              self.stack_name, self.template_status_id,
                              self.resource_type, self.template_type)
        assert (threadId > 0)

    def test_negetive_removeWorker(self):
        self.assertRaises(WorkerThreadError, self.worker.removeWorker,
                          self.threadId)

    def test_removeWorker(self):
        localThreadId = self.worker.getWorker(self.operation,
                                             self.path_to_tempate,
                                             self.stack_name,
                                             self.template_status_id,
                                             self.resource_type,
                                             self.template_type)
        try:
            self.worker.removeWorker(localThreadId)
        except Exception:
            self.fail()

    def test_negetive_execute(self):
        self.assertRaises(WorkerThreadError, self.worker.execute,
                          self.threadId, self.operation)
