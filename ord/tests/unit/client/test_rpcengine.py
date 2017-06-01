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

"""
Unit Tests for ord.client.rpcengine
"""
import copy
from ord.tests import base
from ord.client import rpcengine
from oslo_config import cfg
import stubout

CONF = cfg.CONF


class RpcEngineTestCase(base.BaseTestCase):

    def setUp(self):
        super(RpcEngineTestCase, self).setUp()
        self.stubs = stubout.StubOutForTesting()
        self.addCleanup(self.stubs.UnsetAll)
        self.addCleanup(self.stubs.SmartUnsetAll)

    def _test_api(self, method, rpc_method, **kwargs):

        ctxt = {'request_id': '1'}
        rpcengine_inst = rpcengine.RpcEngine()

        self.assertIsNotNone(rpcengine_inst.target)
        self.assertIsNotNone(rpcengine_inst.transport)
        self.assertIsNotNone(rpcengine_inst._client)
        self.assertEqual(rpcengine_inst.target.topic, 'ord-listener-q')

        expected_retval = 'foo' if method == 'call' else None

        target = {
            "version": kwargs.pop('version', '1.0')
        }

        expected_msg = copy.deepcopy(kwargs)

        self.fake_args = None
        self.fake_kwargs = None

        def _fake_prepare_method(*args, **kwds):
            for kwd in kwds:
                self.assertEqual(kwds[kwd], target[kwd])
            return rpcengine_inst._client

        def _fake_rpc_method(*args, **kwargs):
            self.fake_args = args
            self.fake_kwargs = kwargs
            if expected_retval:
                return expected_retval

        self.stubs.Set(rpcengine_inst._client, "prepare", _fake_prepare_method)
        self.stubs.Set(rpcengine_inst._client, rpc_method, _fake_rpc_method)

        retval = getattr(rpcengine_inst, method)(ctxt, **kwargs)

        self.assertEqual(retval, expected_retval)
        expected_args = [ctxt, method, expected_msg]

        for arg, expected_arg in zip(self.fake_args, expected_args):
            self.assertEqual(arg, expected_arg)

    def test_invoke_listener_rpc(self):
        kwargs = {
            'request_id': '1',
            'resource_id': 'qwe1234',
            'resource-type': 'image'
        }
        payload = str(kwargs)

        self._test_api('invoke_listener_rpc',
                       rpc_method='cast',
                       payload=payload,
                       version='1.0')
