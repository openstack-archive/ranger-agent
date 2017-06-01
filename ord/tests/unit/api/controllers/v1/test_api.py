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
Unit Tests for ord.api.test_api
"""
from ord.tests import base
from ord.api.controllers.v1 import api
from ord.db import api as db_api
from oslo_config import cfg
from mox import stubout
import mock
import requests
import urllib2
import webob

CONF = cfg.CONF


class OrdApiTestCase(base.BaseTestCase):

    PATH_PREFIX = ''

    def setUp(self):
        super(OrdApiTestCase, self).setUp()
        self.stubs = stubout.StubOutForTesting()
        self.addCleanup(self.stubs.UnsetAll)
        self.addCleanup(self.stubs.SmartUnsetAll)

    def test_api_notifier(self):
        ord_notifier = api.NotifierController()

        kwargs = {
            'request_id': '1',
            'resource_id': 'qwe1234',
            'resource-type': 'image'
        }
        payload = str(kwargs)
        params = {
            "ord-notifier": {
                "request-id": "2",
                "resource-id": "1",
                "resource-type": "image",
                "resource-template-version": "1",
                "resource-template-name": "image1",
                "resource-template-type": "hot",
                "operation": "create",
                "region": "local"}
        }

        db_response = {'template_type': u'hot',
                       'status': 'Submitted',
                       'resource_name': u'image1',
                       'resource_operation': u'create',
                       'resource_template_version': u'1',
                       'request_id': '2', 'region': u'local',
                       'resource_id': u'1',
                       'resource_type': u'image',
                       'template_status_id': '1234'}

        CONF.set_default('region', 'local')

        def fake_persist_notification_record(*args, **kwds):
            return db_response

        def fake_invoke_notifier_rpc(*args, **kwds):
            return payload

        self.stubs.Set(ord_notifier, "_persist_notification_record",
                       fake_persist_notification_record)
        self.stubs.Set(ord_notifier._rpcapi, "invoke_notifier_rpc",
                       fake_invoke_notifier_rpc)
        response = ord_notifier.ord_notifier_POST(**params)
        expect_response = response['ord-notifier-response']['status']
        self.assertEqual(expect_response, 'Submitted')

    def test_api_listener(self):
        ctxt = {'request_id': '1'}
        api_listener = api.ListenerQueueHandler()
        kwargs = '{"request_id": "1",'\
                 ' "resource_id": "qwe1234","resource-type": "image"}'
        payload = str(kwargs)
        db_template_target = {'template_type': 'hot',
                              'status': 'STATUS_RDS_SUCCESS',
                              'error_code': '',
                              'error_msg': ''}

        def mock_url_open(mock_response):
            mock_response = mock.Mock()
            mock_response.getcode.return_value = 200

        def urlrequest_mock_method(url, payload, headers):
            return "Failure"

        def fake_update_target(*args, **kwds):
            return db_template_target

        self.stubs.Set(urllib2, 'urlopen', mock_url_open)
        self.stubs.Set(db_api, "update_target_data",
                       fake_update_target)
        self.stubs.Set(urllib2, 'Request', urlrequest_mock_method)
        api_listener.invoke_listener_rpc(ctxt, payload)

    def test_rds_listener_failure(self):
        ctxt = {'request_id': '1'}
        api_listener = api.ListenerQueueHandler()

        kwargs = '{"rds-listener": { "ord-notifier-id": "2",'\
                 '"status": "error","resource-type": "image",'\
                 '"error-code": "","error-msg": ""}}'

        db_template_target = {'template_type': 'hot',
                              'status': 'STATUS_RDS_SUCCESS',
                              'error_code': '',
                              'error_msg': ''}

        payload = str(kwargs)
        output_status = 'STATUS_RDS_SUCCESS'

        def mock_method(url, payload, headers):
            return "Failure"
        self.stubs.Set(urllib2, 'Request', mock_method)

        def mock_url_open(mock_response):
            mock_response = mock.Mock()
            http_error = requests.exceptions.HTTPError()
            mock_response.raise_for_status.side_effect = http_error

        def fake_update_target(*args, **kwds):
            return db_template_target

        self.stubs.Set(urllib2, 'urlopen', mock_url_open)
        self.stubs.Set(db_api, "update_target_data",
                       fake_update_target)
        api_listener.invoke_listener_rpc(ctxt, payload)
        self.assertEqual(output_status, db_template_target['status'])

    def test_rds_listener_success(self):
        ctxt = {'request_id': '1'}
        api_listener = api.ListenerQueueHandler()

        kwargs = '{"rds-listener": { "ord-notifier-id": "2",'\
                 '"status": "error","resource-type": "image",'\
                 '"error-code": "","error-msg": ""}}'

        db_template_target = {'template_type': 'hot',
                              'status': 'Error_RDS_Dispatch',
                              'error_code': '',
                              'error_msg': ''}

        payload = str(kwargs)
        output_status = 'Error_RDS_Dispatch'

        def mock_method(url, payload, headers):
            return "Success"
        self.stubs.Set(urllib2, 'Request', mock_method)

        def mock_url_open(mock_response):
            mock_response = mock.Mock()
            mock_response.getcode.return_value = 200

        def fake_update_target(*args, **kwds):
            return db_template_target

        self.stubs.Set(urllib2, 'urlopen', mock_url_open)
        self.stubs.Set(db_api, "update_target_data",
                       fake_update_target)
        api_listener.invoke_listener_rpc(ctxt, payload)

        self.assertEqual(output_status, db_template_target['status'])

    def test_api_notifier_for_blank_region(self):
        ord_notifier = api.NotifierController()
        params = {
            "ord-notifier": {
                "request-id": "2",
                "resource-id": "1",
                "resource-type": "image",
                "resource-template-version": "1",
                "resource-template-name": "image1",
                "resource-template-type": "hot",
                "operation": "create"}
        }

        self.assertRaises(webob.exc.HTTPBadRequest,
                          ord_notifier.ord_notifier_POST,
                          **params)

    def test_api_notifier_for_invalid_region(self):
        ord_notifier = api.NotifierController()
        params = {
            "ord-notifier": {
                "request-id": "2",
                "resource-id": "1",
                "resource-type": "image",
                "resource-template-version": "1",
                "resource-template-name": "image1",
                "resource-template-type": "hot",
                "operation": "create",
                "region": "dev"}
        }

        CONF.set_default('region', 'local')
        self.assertRaises(webob.exc.HTTPBadRequest,
                          ord_notifier.ord_notifier_POST,
                          **params)

    def test_api_notifier_for_invalid_payload(self):
        ord_notifier = api.NotifierController()
        params = {
            "ord-notifier": {
                "request-id": "2",
                "resource-id": "1",
                "resource-type": "imag e",
                "resource-template-version": "1",
                "resource-template-name": "ima ge1",
                "resource-template-type": "hot",
                "operation": "create",
                "region": "local"}
        }

        CONF.set_default('region', 'local')
        self.assertRaises(webob.exc.HTTPBadRequest,
                          ord_notifier.ord_notifier_POST,
                          **params)

    def test_api_ord_notifier_status(self):
        ord_notifier = api.NotifierController()
        request_id = {"Id": "2"}
        db_template = {'resource_operation': 'create',
              'resource_id': '1',
              'region': 'local',
              'template_type': 'hot',
              'request_id': '2'}

        db_template_target = {'template_type': 'hot',
               'status': 'Submitted',
               'resource_name': 'image1',
               'resource_operation': 'create',
               'resource_template_version': '1',
               'request_id': '2',
               'region': 'local',
               'ord-notifier-id': '1',
               'resource_id': '1',
               'resource_type': 'image',
               'template_status_id': '1',
               'template_version': '1',
               'error_code': 'ORD_000',
               'error_msg': 'stack fail'}

        payload = {'rds-listener':
                   {'request-id': '2',
                    'resource-id': '1',
                    'resource-type': 'image',
                    'resource-template-version': '1',
                    'resource-template-type': 'hot',
                    'resource-operation': 'create',
                    'ord-notifier-id': '1',
                    'region': 'local',
                    'status': 'Submitted',
                    'error-code': 'ORD_000',
                    'error-msg': 'stack fail'}
                   }

        def fake_retrieve_template(*args, **kwds):
            return db_template

        def fake_retrieve_target(*args, **kwds):
            return db_template_target

        self.stubs.Set(db_api, "retrieve_template",
                       fake_retrieve_template)
        self.stubs.Set(db_api, "retrieve_target",
                       fake_retrieve_target)

        notification_status = ord_notifier.ord_notifier_status(**request_id)
        self.assertEqual(payload, notification_status)
