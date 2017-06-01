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

from heatclient import exc as heat_exc
import mock
from ord.client import heat as ord_heat
from ord.tests import base

from ord.common import exceptions as exc


class TestHeatClient(base.BaseTestCase):

    test_template = """heat_template_version: 2015-04-30
                    description: Test stack"""

    dummy_stacks_list = [
        base.Dummy(stack_name='a'),
        base.Dummy(stack_name='bb'),
        base.Dummy(stack_name='ccc')]
    dummy_resource_list = [base.Dummy(resource_type='Image',
                           physical_resource_id='1234')]

    def setUp(self):
        super(TestHeatClient, self).setUp()

        self.clients = mock.Mock()
        self.clients.heat.return_value = self.heat_client,\
            self.keystone_client = mock.Mock(), mock.Mock()
        self.clients.glance.return_value = self.glance_client,\
            self.keystone_client = mock.Mock(), mock.Mock()
        self.patch('ord.client.heat.Clients').return_value = self.clients

        self.heat = ord_heat.HeatClient()

    def test_get_stacks(self):
        self.heat_client.stacks.list.return_value = self.dummy_stacks_list

        result = self.heat.get_stacks()
        self.assertEqual(self.dummy_stacks_list, result)

    def test_get_stack(self):
        stack_idnr = "1"
        stack = self.dummy_stacks_list[0]
        self.heat_client.stacks.get.return_value = stack

        result = self.heat.get_stack(stack_idnr)
        self.assertEqual(stack, result)
        self.heat_client.stacks.get.assert_called_with(stack_idnr)

    def test_get_stack_by_name(self):
        name = self.dummy_stacks_list[-1].stack_name
        self.heat_client.stacks.list.return_value = self.dummy_stacks_list

        result = self.heat.get_stack_by_name(name)
        self.assertEqual(self.dummy_stacks_list[-1], result)

    def test_get_stack_by_name_fail(self):
        name = 'force-name-mismatch-{}'.format(
            self.dummy_stacks_list[-1].stack_name)
        self.heat_client.stacks.list.return_value = self.dummy_stacks_list

        self.assertRaises(
            exc.HEATLookupError, self.heat.get_stack_by_name, name)

    def test_create_stack(self):
        stack_name = "test_stack"
        template = self.make_tempfile(
            prefix='heat-create', payload=self.test_template)

        self.heat.create_stack(stack_name, template.name)

        self.heat_client.stacks.create.assert_called_once_with(
            stack_name=stack_name, template=self.test_template)

    def test_update_stack(self):
        stack_idnr = "1"
        template = self.make_tempfile(
            prefix='heat-update', payload=self.test_template)

        self.heat.update_stack(stack_idnr, template.name)
        self.heat_client.stacks.update.assert_called_once_with(
            stack_idnr, template=self.test_template)

    def test_delete_stack(self):
        stack_idnr = "1"
        self.heat.delete_stack(stack_idnr)
        self.heat_client.stacks.delete.assert_called_with(stack_idnr)

    def test_error_masquerading(self):
        error = heat_exc.CommunicationError('ord-heat-stack-create-test')

        stack_idnr = '0'
        stack_name = "test_stack"
        template = self.make_tempfile(
            prefix='head-create', payload=self.test_template)

        h = self.heat_client
        for mock_call, method, args in (
                (h.stacks.list, self.heat.get_stacks, ()),
                (h.stacks.create, self.heat.create_stack,
                    (stack_name, template.name)),
                (h.stacks.update, self.heat.update_stack,
                    (stack_idnr, template.name)),
                (h.stacks.delete, self.heat.delete_stack, (stack_idnr,))):
            mock_call.side_effect = error

            if not args:
                args = tuple()
            self.assertRaises(
                exc.HEATIntegrationError, method, *args)

    def get_image_data_by_stackid(self):
        stack_id = '1234'
        self.heat_client.resources.list.return_value = self.dummy_resource_list
        image_data = 'new_image'
        self.glance_client.images.get.return_value = image_data
        result = self.heat.get_image_data_by_stackid(stack_id)
        self.assertEqual(image_data, result)
