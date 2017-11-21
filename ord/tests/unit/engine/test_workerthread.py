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

import itertools
import os

import mock
from oslo_config import cfg

from ord.common import exceptions as exc
from ord.common import utils
from ord.engine import workerfactory
from ord.tests import base

CONF = cfg.CONF


# FIXME(db2242): pep8 compatible - camelcase attributes
class TestWorkerThread(base.BaseTestCase):

    def setUp(self):
        super(TestWorkerThread, self).setUp()

        self.operation = utils.OPERATION_CREATE
        self.path_to_tempate = 'test_path'
        self.stack_name = 'test_stack'
        self.template_status_id = '1'
        self.resource_type = 'image'
        self.template_type = 'hot'
        self.threadId = 123
        self.local_repo = 'aic-orm-resources-labs'

        self._temp_repo_client = mock.Mock()
        self._temp_repo_client.pull_template.return_value = self.pull_client\
            = mock.Mock()
        self.patch('ord.engine.workerfactory.getrepo').return_value\
            = self._temp_repo_client

        self.db_api = mock.Mock()
        self.db_api.update_target_data.return_value = self.db_client\
            = mock.Mock()
        self.patch('ord.db.sqlalchemy.api').return_value\
            = self.db_api

        self.WorkerFactory = mock.Mock()
        self.WorkerFactory.removeWorker.return_value = self.remove_clinet\
            = mock.Mock()
        self.patch('ord.engine.workerfactory.WorkerFactory').return_value\
            = self.WorkerFactory

        self.workerThread = workerfactory.WorkerThread(
            self.threadId, self.operation, self.path_to_tempate,
            self.stack_name, self.template_status_id,
            self.resource_type)
        self.workerThread._heat_client = self.heat_client = mock.Mock()
        self.workerThread._temp_repo_client = self._temp_repo_client
        self.workerThread.db_api = self.db_api

    def test_extract_resource_extra_metadata(self):
        stack = base.Dummy(id='1', stack_name=self.stack_name)
        image_data = {'checksum': 'dae557b1365b606e57fbd5d8c9d4516a',
                      'size': '10',
                      'virtual_size': '12'}
        input_payload = {'rds-listener':
                         {'request-id': '2',
                          'resource-id': '1',
                          'resource-operation': 'create',
                          'resource-type': 'image'}
                         }
        output_payload = {'rds-listener':
                          {'request-id': '2',
                           'resource-id': '1',
                           'resource-operation': 'create',
                           'resource-type': 'image',
                           'resource_extra_metadata':
                               {'checksum': 'dae557b1365b606e57fbd5d8c9d4516a',
                                'size': '10',
                                'virtual_size': '12'}}}

        self.heat_client.get_stack_by_name.return_value = stack
        self.heat_client.get_image_data_by_stackid.return_value = image_data
        self.workerThread.extract_resource_extra_metadata(
            input_payload, utils.STATUS_SUCCESS)

        self.heat_client.get_stack_by_name.assert_called_once_with(
            stack.stack_name)
        self.heat_client.\
            get_image_data_by_stackid.assert_called_once_with(stack.id)
        self.assertEqual(output_payload, input_payload)

    def test_fetch_template(self):
        self.workerThread._fetch_template()
        self._temp_repo_client.pull_template\
            .assert_called_with(self.local_repo, self.path_to_tempate)

    def test_create_stack(self):
        self.heat_client.create_stack.return_value = {'stack': {'id': 1}}
        template = os.path.join(
            os.path.expanduser('~'), self.local_repo, self.path_to_tempate)

        self.workerThread._create_stack(template)

        self.heat_client.create_stack.assert_called_once_with(
            self.stack_name, template)

    def test_update_stack(self):
        stack = base.Dummy(id='1', stack_name=self.stack_name)
        template = os.path.join(
            os.path.expanduser('~'), self.local_repo, self.path_to_tempate)

        self.heat_client.get_stack_by_name.return_value = stack

        self.workerThread._update_stack(template)

        self.heat_client.get_stack_by_name.assert_called_once_with(
            self.stack_name)
        self.heat_client.update_stack.\
            assert_called_with(stack.id, template)

    def test_delete_stack(self):
        stack = base.Dummy(id='1', stack_name=self.stack_name)
        self.heat_client.get_stack_by_name.return_value = stack

        self.workerThread._delete_stack()

        self.heat_client.get_stack_by_name.assert_called_once_with(
            stack.stack_name)
        self.heat_client.delete_stack.assert_called_once_with(stack.id)

    def test_wait_for_heat(self):
        time_time = self.patch('time.time', side_effect=itertools.count(1))
        time_sleep = self.patch('time.sleep')

        stack_wait = base.Dummy(
            id='1', stack_name=self.stack_name,
            stack_status='CREATE_IN_PROGRESS')
        stack_ready = base.Dummy(
            id='1', stack_name=self.stack_name, stack_status='CREATE_COMPLETE')
        status_responses = [stack_wait] * 4 + [stack_ready]

        self.heat_client.get_stack.side_effect = status_responses

        # raise exception in case of failure
        self.workerThread._wait_for_heat(stack_wait, utils.OPERATION_CREATE)

        self.assertEqual(
            [mock.call(CONF.heat_poll_interval)] * 5,
            time_sleep.mock_calls)
        self.assertEqual(6, time_time.call_count)

    def test_wait_for_heat_fail(self):
        self.patch('time.time', side_effect=itertools.count(1))
        self.patch('time.sleep')

        stack_wait = base.Dummy(
            id='1', stack_name=self.stack_name,
            stack_status='CREATE_IN_PROGRESS')
        stack_ready = base.Dummy(
            id='1', stack_name=self.stack_name, stack_status='CREATE_FAILED',
            stack_status_reason='Stack fail due to resource creation')

        status_responses = [stack_wait] * 4 + [stack_ready]

        self.heat_client.get_stack.side_effect = status_responses

        self.assertRaises(
            exc.HEATStackCreateError, self.workerThread._wait_for_heat,
            stack_wait, utils.OPERATION_CREATE)

    def test_wait_for_heat_race(self):
        self.patch('time.time', side_effect=itertools.count(1))
        self.patch('time.sleep')

        stack_initial = base.Dummy(
            id='1', stack_name=self.stack_name, stack_status='UPDATE_COMPLETE',
            updated_time='2016-06-02T16:30:48Z')
        stack_wait = base.Dummy(
            id='1', stack_name=self.stack_name,
            stack_status='UPDATE_IN_PROGRESS',
            updated_time='2016-06-02T16:30:48Z')
        stack_ready = base.Dummy(
            id='1', stack_name=self.stack_name, stack_status='UPDATE_COMPLETE',
            updated_time='2016-06-02T16:30:50Z')
        status_responses = [stack_initial]
        status_responses += [stack_wait] * 2
        status_responses += [stack_ready]

        status_transition = workerfactory.StatusTransitions('_unittest_')
        self.patch(
            'ord.engine.workerfactory.StatusTransitions',
            return_value=status_transition)

        self.heat_client.get_stack.side_effect = status_responses

        self.workerThread._wait_for_heat(stack_initial, utils.OPERATION_MODIFY)

        self.assertEqual('UPDATE_COMPLETE', status_transition.transitions[-1])

    def test_run(self):
        self.workerThread._execute_operation = execute = mock.Mock()
        execute.return_value = 'OPERATION_STATUS'
        self.workerThread._update_permanent_storage = \
            save_results = mock.Mock()
        self.workerThread._send_operation_results = send_results = mock.Mock()

        self.workerThread.run()

        execute.assert_called_with()
        save_results.assert_called_once_with()
        send_results.assert_called_once_with()

    def test_run_fail(self):
        error = exc.StackOperationError(operation='unittest', stack='dummy')

        self.workerThread._execute_operation = execute = mock.Mock(
            side_effect=error)
        self.workerThread._update_permanent_storage = save_status = mock.Mock()
        self.workerThread._send_operation_results = send_results = mock.Mock()

        self.workerThread.run()

        execute.assert_called_once_with()
        save_status.assert_called_once_with(error)
        send_results.assert_called_once_with()

    def test_run_fail_uncontrolled(self):
        error = ZeroDivisionError()

        self.workerThread._execute_operation = execute = mock.Mock(
            side_effect=error)
        self.workerThread._update_permanent_storage = save_status = mock.Mock()
        self.workerThread._send_operation_results = send_results = mock.Mock()

        self.workerThread.run()

        execute.assert_called_once_with()

    def test_update_permanent_storage(self):
        db_api = self.patch('ord.engine.workerfactory.db_api')

        self.workerThread._update_permanent_storage()
        db_api.update_target_data.assert_called_once_with(
            self.template_status_id, utils.STATUS_SUCCESS,
            error_code=exc.SUCCESS_CODE)

    def test_update_permanent_storage_error(self):
        db_api = self.patch('ord.engine.workerfactory.db_api')

        generic_error = ZeroDivisionError()
        ord_error = exc.IntegrationError('unit-test')
        stack_error = exc.StackOperationError(
            stack='ord-stack-error-without-rollback', operation='unit-test')
        stack_error_rollback = exc.StackOperationError(
            stack='ord-stack-error-with-rollback',
            operation=utils.OPERATION_CREATE, rollback_status=True)
        stack_error_rollback_fail0 = exc.StackOperationError(
            stack='ord-stack-error-with-rollback-fail',
            operation=utils.OPERATION_CREATE, rollback_status=False)
        stack_error_rollback_fail1 = exc.StackOperationError(
            stack='ord-stack-error-with-rollback-fail-and-message',
            operation=utils.OPERATION_CREATE, rollback_status=False,
            rollback_message='a\nbb\nccc')

        for error, status, error_code, error_message in (
                (generic_error, utils.STATUS_INTERNAL_ERROR,
                    exc.ERROR_UNKNOWN_EXCEPTION, str(generic_error)),
                (ord_error, utils.STATUS_INTERNAL_ERROR,
                    ord_error.error_code, ord_error.message),
                (stack_error, utils.STATUS_ERROR,
                    stack_error.error_code, stack_error.message),
                (stack_error_rollback, utils.STATUS_ERROR,
                    stack_error_rollback.error_code,
                    '{}\n[ROLLBACK] success'.format(
                        stack_error_rollback.message)),
                (stack_error_rollback_fail0, utils.STATUS_ERROR,
                    stack_error_rollback_fail0.error_code,
                    '{}\n[ROLLBACK] fail'.format(
                        stack_error_rollback_fail0.message)),
                (stack_error_rollback_fail1, utils.STATUS_ERROR,
                 stack_error_rollback_fail1.error_code,
                 '{}\n[ROLLBACK] a\n[ROLLBACK] bb\n[ROLLBACK] ccc'.format(
                     stack_error_rollback_fail1.message))):
            self.workerThread._update_permanent_storage(error)

            db_api.update_target_data.assert_called_once_with(
                self.template_status_id, status,
                error_code=error_code, error_msg=error_message)
            db_api.update_target_data.reset_mock()


class TestStatusTransitions(base.BaseTestCase):
    def test(self):
        for data, expect in [
                ('A', 'A'),
                ('AA', 'A(2)'),
                ('ABC', 'A ~> B ~> C'),
                ('AABBCC', 'A(2) ~> B(2) ~> C(2)')]:
            subject = workerfactory.StatusTransitions(data[0])
            for entity in data[1:]:
                subject.add(entity)
            self.assertEqual(expect, str(subject))


class TestHEATIntermediateStatusChecker(base.BaseTestCase):
    def test_scenario(self):
        cls = workerfactory.HEATIntermediateStatusChecker

        scenario_create = [
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_CREATE, cls.STATUS_IN_PROGRESS))),
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_CREATE, cls.STATUS_COMPLETE)))]

        scenario_create_fail = [
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_CREATE, cls.STATUS_IN_PROGRESS))),
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_CREATE, cls.STATUS_FAIL)))]
        scenario_delete = [
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_CREATE, cls.STATUS_COMPLETE))),
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_DELETE, cls.STATUS_IN_PROGRESS))),
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_DELETE, cls.STATUS_COMPLETE)))]
        scenario_delete_fail = [
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_CREATE, cls.STATUS_COMPLETE))),
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_DELETE, cls.STATUS_IN_PROGRESS))),
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_DELETE, cls.STATUS_FAIL)))]
        scenario_update = [
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_CREATE, cls.STATUS_COMPLETE))),
            base.Dummy(
                updated_time=None, stack_status='_'.join((
                    cls.ACTION_UPDATE, cls.STATUS_IN_PROGRESS))),
            base.Dummy(
                updated_time='2016-06-02T16:30:00Z', stack_status='_'.join((
                    cls.ACTION_UPDATE, cls.STATUS_COMPLETE)))]
        scenario_update_update = [
            base.Dummy(
                updated_time='2016-06-02T16:30:00Z', stack_status='_'.join((
                    cls.ACTION_UPDATE, cls.STATUS_COMPLETE))),
            base.Dummy(
                updated_time='2016-06-02T16:30:00Z', stack_status='_'.join((
                    cls.ACTION_UPDATE, cls.STATUS_COMPLETE))),
            base.Dummy(
                updated_time='2016-06-02T16:30:00Z', stack_status='_'.join((
                    cls.ACTION_UPDATE, cls.STATUS_IN_PROGRESS))),
            base.Dummy(
                updated_time='2016-06-02T16:30:01Z', stack_status='_'.join((
                    cls.ACTION_UPDATE, cls.STATUS_COMPLETE)))]

        for scenario, operation, is_fail in (
                (scenario_create, utils.OPERATION_CREATE, False),
                (scenario_create_fail, utils.OPERATION_CREATE, True),
                (scenario_delete, utils.OPERATION_DELETE, False),
                (scenario_delete_fail, utils.OPERATION_DELETE, True),
                (scenario_update, utils.OPERATION_MODIFY, False),
                (scenario_update_update, utils.OPERATION_MODIFY, False)):
            status_check = cls(scenario[0], operation)
            for step in scenario[:-1]:
                self.assertEqual(True, status_check(step))
            self.assertEqual(False, status_check(scenario[-1]))
            self.assertEqual(is_fail, status_check.is_fail)

    def test_extract_action_and_status(self):
        cls = workerfactory.HEATIntermediateStatusChecker
        stack = base.Dummy(stack_status='a_b_c')
        action, status = cls._extract_action_and_status(stack)

        self.assertEqual('a', action)
        self.assertEqual('b_c', status)

    def test_extract_action_and_status_fail(self):
        cls = workerfactory.HEATIntermediateStatusChecker
        stack = base.Dummy(stack_status='abc')
        self.assertRaises(
            exc.HEATIntegrationError, cls._extract_action_and_status, stack)
