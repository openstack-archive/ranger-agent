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

import datetime

import mock
from ord.db.sqlalchemy import api as db_api
from ord.tests import base


class TestORDNotify(base.BaseTestCase):

    def _prepare_fake_message(self):
        fake_input = {"request_id": "fake_req",
                      "resource_id": "fake_res",
                      "template_type": "hot",
                      "resource_operation": "create",
                      "region": "fake_region",
                      "time_stamp": datetime.datetime.now(),
                      "template_status_id": "fake_id",
                      "resource_template_version": "fake_ver",
                      "resource_name": "fake_name",
                      "resource_type": "fake_type",
                      "status": "submitted",
                      "error_code": "",
                      "error_msg": ""
                      }
        return fake_input

    def setUp(self):
        super(TestORDNotify, self).setUp()
        self.mock_db_api = mock.Mock()
        self.patch(
            'ord.db.sqlalchemy.api.get_session').return_value = mock.Mock()
        self.patch(
            'ord.db.sqlalchemy.api.get_engine').return_value = mock.Mock()

    @mock.patch.object(db_api, 'get_session')
    def test_create_ord_data(self, mock_session):
        input_msg = self._prepare_fake_message()
        db_api.create_template(input_msg)
        mock_session.assert_called_once_with()

    @mock.patch.object(db_api, 'get_session')
    @mock.patch.object(db_api, 'create_target')
    def test_create_ord_target_data(self, mock_taget, mock_session):
        input_msg = self._prepare_fake_message()
        db_api.create_template(input_msg)
        mock_session.assert_called_once_with()
        assert mock_taget.called

    @mock.patch.object(db_api, 'get_session')
    @mock.patch.object(db_api, 'model_query')
    def test_retrieve_ord_data(self, mock_query, mock_session):
        db_api.retrieve_template("fake_res")
        mock_session.assert_called_once_with()
        assert mock_query.called

    @mock.patch.object(db_api, 'get_session')
    @mock.patch.object(db_api, 'model_query')
    def test_retrieve_target_data(self, mock_query, mock_session):
        db_api.retrieve_target("fake_res")
        mock_session.assert_called_once_with()
        assert mock_query.called

    @mock.patch.object(db_api, 'get_session')
    @mock.patch.object(db_api, 'model_query')
    def test_retrieve_target_data_by_status(self, mock_query, mock_session):
        db_api.retrieve_target_by_status("fake_id")
        mock_session.assert_called_once_with()
        assert mock_query.called
