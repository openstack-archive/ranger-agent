# Copyright (c) 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from heatclient import exc as heat_exc

from ord.client.client import Clients
from ord.common import exceptions as exc
from ord.common import utils


class HeatClient(object):

    _kc = None

    def __init__(self):
        # FIXME: we must not cache any clients because it done(must
        # be done) by "Clients"
        try:
            if HeatClient._kc is None:
                HeatClient._kc = Clients().keystone()
        except Exception as e:
            raise exc.KeystoneInitializationException(e.message)

    def get_stacks(self):
        client, self._kc = Clients().heat(self._kc)
        try:
            payload = client.stacks.list()
        except heat_exc.BaseException as e:
            raise exc.HEATIntegrationError(
                action='stacks.list', details=e.message)
        return payload

    def get_stack(self, stack_id):
        client, self._kc = Clients().heat(self._kc)
        try:
            payload = client.stacks.get(stack_id)
            # TODO: check behaviour in case it object not exist
        except heat_exc.BaseException as e:
            raise exc.HEATIntegrationError(
                action='stacks.get', details=e.message)
        return payload

    # TODO: check real heatclient capabilities to lookup objects
    def get_stack_by_name(self, name):
        for stack in self.get_stacks():
            if stack.stack_name != name:
                continue
            break
        else:
            raise exc.HEATStackLookupError(query='name={!r}'.format(name))
        return stack

    def create_stack(self, name, template):
        template = utils.load_file(template)

        client, self._kc = Clients().heat(self._kc)
        try:
            response = client.stacks.create(
                stack_name=name, template=template)
        except heat_exc.BaseException as e:
            raise exc.HEATStackCreateError(details=e.message)
        return response

    def update_stack(self, stack_id, template):
        template = utils.load_file(template)
        client, self._kc = Clients().heat(self._kc)

        try:
            response = client.stacks.update(stack_id, template=template)
        except heat_exc.BaseException as e:
            raise exc.HEATStackUpdateError(details=e.message)
        return response

    def delete_stack(self, stack_id):
        client, self._kc = Clients().heat(self._kc)
        try:
            client.stacks.delete(stack_id)
        except heat_exc.BaseException as e:
            raise exc.HEATStackDeleteError(details=e.message)

    def get_image_data_by_stackid(self, stack_id):
        client, self._kc = Clients().heat(self._kc)
        resources = client.resources.list(stack_id)
        image_id = None
        image_data = None
        for resource in resources:
            if utils.RESOURCE_IMAGE in resource.resource_type:
                image_id = resource.physical_resource_id
        glance_client = Clients().glance(self._kc)
        if image_id:
            image_data = glance_client.images.get(image_id)
        return image_data
