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

import itertools
import json
import os
from oslo_config import cfg
from random import SystemRandom
import six
import sys
import threading
import time

from ord.client import getrepo
from ord.client import heat
from ord.client import rpcengine
from ord.common import exceptions as exc
from ord.common import utils
from ord.db.sqlalchemy import api as db_api
from ord.openstack.common import log as logging


CONF = cfg.CONF

CONF.register_opts([
    cfg.StrOpt('local_repo', default='aic-orm-resources-labs',
               help='local repo from where the'
                    'template yaml can be accessed from'),
    cfg.IntOpt('heat_poll_interval', default=5,
               help='delay in seconds between two consecutive call to '
                    'heat.stacks.status'),
    cfg.IntOpt('resource_status_check_wait', default=10,
               help='delay in seconds between two retry call to '
                    'rds listener repo'),
    cfg.Opt('retry_limits',
            default='3',
            help='number of retry'),
    cfg.Opt('enable_rds_callback_check',
            default=True,
            help='validate rds api is reachable'),
    cfg.IntOpt('resource_creation_timeout_min', default=1200,
               help='max wait time for flavor and customer stacks'),
    cfg.IntOpt('resource_creation_timeout_max', default=14400,
               help='max wait time for image stacks')
])

LOG = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = \
                super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


@six.add_metaclass(Singleton)
class WorkerFactory(object):
    _instance = None
    _temp_repo_client = None
    _heat_client = None
    _glance_client = None
    _db_client = None
    _rpcengine = None
    _client_initialize = False
    _threadPool = {}
    _init_error = None

    @staticmethod
    def _client_init():
        LOG.info("Initializing all clients :: %s",
                 str(WorkerFactory._client_initialize))
        WorkerThread._init_error = None
        try:

            WorkerThread._temp_repo_client = \
                getrepo.TemplateRepoClient(CONF.local_repo)

            WorkerThread._heat_client = heat.HeatClient()

            try:
                WorkerThread._rpcengine = rpcengine.RpcEngine()
            except exc.RPCInitializationException as rpcexp:
                LOG.critical("Failed to initialize RPC %s ", rpcexp)
                WorkerThread._init_error = utils.ErrorCode.ORD_019.value

        except Exception as exception:
            WorkerThread._init_error = utils.ErrorCode.ORD_017.value
            LOG.critical(
                "Unexpected error while initializing clients %s" % exception)
        finally:
            WorkerThread._threadPool = {}
            if WorkerThread._init_error is None:
                WorkerThread._client_initialize = True

    @classmethod
    def removeWorker(cls, idnr):
        LOG.info("Deleting thread : " + str(idnr))
        try:
            del WorkerThread._threadPool[idnr]
        except KeyError:
            LOG.info("Thread was not found for deletion")
            raise exc.WorkerThreadError(thread_id=idnr)
        LOG.info("Thread was deleted : " + str(idnr))

    def __init__(self):
        LOG.info("initializing WorkerFactory._init_")
        if WorkerFactory._client_initialize is False:
            WorkerFactory._client_init()
        WorkerThread._client_initialize = True

    def getWorker(self, operation, path_to_tempate, stack_name,
                  template_status_id, resource_type,
                  template_type):
        template_type = template_type.lower()

        # FIXME: this code have a none zero to fail in very unexpected
        # way
        randCrypt = SystemRandom()
        threadID = randCrypt.randint(1, 99999999)
        if template_type == "hot":
            miniWorker = WorkerThread(threadID, operation,
                                      path_to_tempate, stack_name,
                                      template_status_id, resource_type,
                                      WorkerThread._init_error)
            WorkerThread._threadPool.update({threadID: miniWorker})
        elif template_type == "ansible":
            threadID = -1
        else:
            # FIXME: too late for such check
            raise exc.UnsupportedTemplateTypeError(template=template_type)
        return threadID

    def execute(self, idnr, operation):
        try:
            worker = WorkerThread._threadPool[idnr]
        except KeyError:
            raise exc.WorkerThreadError(thread_id=idnr)
        worker.start()


class WorkerThread(threading.Thread):

    def __init__(self, threadID, operation, path_to_tempate, stack_name,
                 template_status_id, resource_type, client_error=None):
        LOG.info("initializing Thread._init_")
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.operation = operation
        self.template_path = path_to_tempate
        self.stack_name = stack_name
        self.template_status_id = template_status_id
        self.resource_type = resource_type
        self.client_error = client_error

    def extract_resource_extra_metadata(self, rds_payload, rds_status):
        resource_operation =\
            rds_payload.get('rds-listener')['resource-operation']
        if self.resource_type.lower() == 'image' \
                and rds_status == utils.STATUS_SUCCESS\
                and resource_operation != utils.OPERATION_DELETE:
            stack = self._heat_client.get_stack_by_name(self.stack_name)
            image_data = self._heat_client.get_image_data_by_stackid(stack.id)
            if image_data:
                rds_payload.get('rds-listener').update(
                    {'resource_extra_metadata':
                        {'checksum': image_data['checksum'],
                         'size': str(image_data['size']),
                         'virtual_size':
                            str(image_data['virtual_size'])}})

    def _prepare_rds_payload(self):
        target_data = db_api.retrieve_target_by_status(self.template_status_id)
        notify_data = {}
        if 'request_id' in target_data:
            notify_data = db_api.retrieve_template(
                target_data.get('request_id'))

        payload = utils.create_rds_payload(notify_data, target_data)
        return payload

    def run(self):
        LOG.debug("Thread Starting :: %s", self.threadID)
        LOG.debug("operation=%s, stack_name=%s, path_to_tempate=%s",
                  self.operation, self.stack_name, self.template_path)
        template_absolute_path = self.template_path
        try:
            if self._is_engine_initialized():
                LOG.debug('Client initialization complete')
                try:
                    template_absolute_path = self._fetch_template()
                    self._execute_operation(template_absolute_path)
                except exc.ORDException as e:
                    LOG.error('%s', e.message)
                    self._update_permanent_storage(e)
                except Exception as e:
                    LOG.critical('Unhandled exception into %s',
                                 type(self).__name__, exc_info=True)
                    self._update_permanent_storage(e)
                else:
                    self._update_permanent_storage()

            try:
                self._send_operation_results()
            except Exception:
                LOG.critical('ORD_019 - INCOMPLETE OPERATION! Error during '
                             'sending operation results. Called will never '
                             'know about issue.')
                raise
        except Exception:
            LOG.critical('Unhandled exception into %s', type(self).__name__,
                         exc_info=True)
        finally:
            self._cleanup_template(template_absolute_path)
            LOG.info("Thread Exiting :: %s", self.threadID)
            WorkerFactory.removeWorker(self.threadID)

    def _is_engine_initialized(self):
        args = {}
        if self.client_error is not None:
            args['error_code'] = self.client_error
            args['error_msg'] = utils.ErrorCode.tostring(self.client_error)
            LOG.debug('Updating DB with %s code with %s '
                      % (args['error_code'], args['error_msg']))
            db_api.update_target_data(
                self.template_status_id, utils.STATUS_ERROR, **args)
            return False
        return True

    def _execute_operation(self, template):

        if self.operation == utils.OPERATION_CREATE:
            stack = self._create_stack(template)
        elif self.operation == utils.OPERATION_MODIFY:
            stack = self._update_stack(template)
        elif self.operation == utils.OPERATION_DELETE:
            stack = self._delete_stack()
        else:
            raise exc.UnsupportedOperationError(operation=self.operation)

        try:
            self._wait_for_heat(stack, self.operation)
        except exc.ORDException:
            _, e, _tb = sys.exc_info()
            if self.operation == utils.OPERATION_CREATE:

                args = {}
                try:
                    stack = self._delete_stack()
                    self._wait_for_heat(
                        stack, utils.OPERATION_DELETE)
                except exc.ORDException as e_rollback:
                    args['rollback_error'] = e_rollback
                    args['rollback_message'] = e_rollback.message
                    args['rollback_status'] = False
                else:
                    args['rollback_status'] = True

            raise

    def _cleanup_template(self, template_absolute_path):
        LOG.info("Removing template File :: %s", template_absolute_path)
        try:
            if os.path.isfile(template_absolute_path):
                os.remove(template_absolute_path)
                LOG.info("Template File Removed")
        except Exception as ex:
            LOG.error("Error on cleanup of template File :: %s", ex)

    def _update_permanent_storage(self, error=None):
        args = {}
        if isinstance(error, exc.StackOperationError):
            status = utils.STATUS_ERROR
            args['error_msg'] = error.message
            args['error_code'] = error.error_code
            try:
                rollback = error.arguments['rollback_status']
            except KeyError:
                pass
            else:
                if rollback:
                    rollback_message = 'success'
                else:
                    rollback_message = error.arguments.get(
                        'rollback_message', 'fail')
                glue = '\n[ROLLBACK] '
                rollback_message = glue.join(rollback_message.split('\n'))
                args['error_msg'] = glue.join(
                    (args['error_msg'], rollback_message))
        elif isinstance(error, exc.ORDException):
            status = utils.STATUS_INTERNAL_ERROR
            args['error_msg'] = error.message
            args['error_code'] = error.error_code
        elif isinstance(error, Exception):
            status = utils.STATUS_INTERNAL_ERROR
            args['error_msg'] = str(error)
            args['error_code'] = exc.ERROR_UNKNOWN_EXCEPTION
        else:
            args['error_code'] = exc.SUCCESS_CODE
            status = utils.STATUS_SUCCESS

        db_api.update_target_data(
            self.template_status_id, status, **args)

    def _send_operation_results(self):
        if CONF.orm.enable_rds_callback_check:
            rds_payload = self._prepare_rds_payload()
            res_ctxt = \
                {'request-id': rds_payload.get('rds-listener')['request-id']}
            LOG.debug("----- RPC API Payload to RDS %r", rds_payload)
            status_original = rds_payload.get('rds-listener')['status']

            try:
                self.extract_resource_extra_metadata(rds_payload,
                                                     status_original)
            except Exception as exception:
                LOG.error("Unexpected error collecting extra \
                Image Parameter %s", exception)

            max_range = int(CONF.orm.retry_limits)
            self._rpcengine. \
                invoke_listener_rpc(res_ctxt, json.dumps(rds_payload))
            while max_range - 1 > 0:
                LOG.debug('Waiting for invoke listener')
                time.sleep(CONF.resource_status_check_wait)
                target_data = db_api.retrieve_target_by_status(
                    self.template_status_id)
                status = target_data.get('status')
                if status == utils.STATUS_RDS_ERROR:
                    LOG.debug("Retrying for RDS listener response %s",
                              max_range)
                    rds_payload.get('rds-listener')['status'] = status_original
    #                if image_payload:
    #                   rds_payload.get('rds-listener')['status']
    #                        = image_payload
                    self._rpcengine. \
                        invoke_listener_rpc(res_ctxt, json.dumps(rds_payload))

                if status != utils.STATUS_RDS_SUCCESS:
                    LOG.debug("Retrying for api response")
                    max_range = max_range - 1
                else:
                    break
        else:
            LOG.debug("RPC callback check disabled")

    def _fetch_template(self):
        """Fetch template from document storage

        Template fetching will be skipped if current operation does not require
        template.
        """
        if self.operation not in (
                utils.OPERATION_CREATE,
                utils.OPERATION_MODIFY):
            return

        LOG.debug("template path: %r", self.template_path)
        return self._temp_repo_client.pull_template(
            CONF.local_repo, self.template_path)

    def _create_stack(self, template):
        LOG.debug("Creating stack name %s by template %s",
                  self.stack_name, self.template_path)
        # This call return raw response(dict), but all other calls to heat
        # client return "models" build from raw responses. Look like this a
        # BUG into heatclient. This behavior is not fixed until now (1.2.0).
        stack = self._heat_client.create_stack(self.stack_name, template)
        stack = stack['stack']
        return self._heat_client.get_stack(stack['id'])

    def _update_stack(self, template):
        LOG.debug("Updating stack id %s by template %s",
                  self.stack_name, self.template_path)

        stack = self._heat_client.get_stack_by_name(self.stack_name)
        self._heat_client.update_stack(stack.id, template)
        return stack

    def _delete_stack(self):
        LOG.info("Deleting stack %r", self.stack_name)

        stack = self._heat_client.get_stack_by_name(self.stack_name)
        self._heat_client.delete_stack(stack.id)
        return stack

    def _wait_for_heat(self, stack, operation):
        LOG.debug('Wait while HEAT do his job: stack=%s', self.stack_name)

        poll_interval = CONF.heat_poll_interval
        LOG.debug("HEAT poll interval: %s", poll_interval)
        max_wait_time = 0
        if self.resource_type == 'image':
            max_wait_time = CONF.resource_creation_timeout_max
        else:
            max_wait_time = CONF.resource_creation_timeout_min
        LOG.debug("max_wait_time: %s", max_wait_time)

        stack_status_transitions = StatusTransitions(stack.stack_status)

        start_time = time.time()
        waiting_time = 0
        status_check = HEATIntermediateStatusChecker(stack, operation)
        while status_check(stack) \
                and (waiting_time <= max_wait_time):
            time.sleep(poll_interval)
            waiting_time = time.time() - start_time

            LOG.debug('%s waiting %s for %s',
                      self.threadID, waiting_time,
                      stack.stack_name)
            LOG.debug('%s stack status transition: %s',
                      self.threadID, stack_status_transitions)

            stack = self._heat_client.get_stack(stack.id)
            stack_status_transitions.add(stack.stack_status)

        LOG.debug('%s done with waiting for stack %s: action=%s, status=%s',
                  self.threadID, stack.stack_name, status_check.action,
                  status_check.status)

        if status_check.is_fail:
            if operation == utils.OPERATION_CREATE:
                raise exc.HEATStackCreateError(
                    details=stack.stack_status_reason)
            elif operation == utils.OPERATION_MODIFY:
                raise exc.HEATStackUpdateError(
                    details=stack.stack_status_reason)
            elif operation == utils.OPERATION_DELETE:
                raise exc.HEATStackDeleteError(
                    details=stack.stack_status_reason)
            else:
                raise exc.StackOperationError(
                    operation=operation, stack=stack)
        elif status_check.is_in_progress:
            raise exc.StackTimeoutError(operation=operation, stack=stack)


class StatusTransitions(object):

    def __init__(self, status):
        self.transitions = [status]
        self.hits = [1]

    def add(self, status):
        if self.transitions[-1] != status:
            self.transitions.append(status)
            self.hits.append(0)
        self.hits[-1] += 1

    def __str__(self):
        chunks = []
        for status, hits in itertools.izip(self.transitions, self.hits):
            if 1 < hits:
                status = '{}({})'.format(status, hits)
            chunks.append(status)
        return ' ~> '.join(chunks)


class HEATIntermediateStatusChecker(object):
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETE = 'COMPLETE'
    STATUS_FAIL = 'FAILED'

    _operation_to_heat_action_map = {
        utils.OPERATION_CREATE: ACTION_CREATE,
        utils.OPERATION_MODIFY: ACTION_UPDATE,
        utils.OPERATION_DELETE: ACTION_DELETE}

    def __init__(self, stack, operation):
        self.stack = stack
        self.expect_action = self._operation_to_heat_action_map[operation]
        self.action, self.status = self._extract_action_and_status(self.stack)

    def __call__(self, stack):
        self.action, self.status = self._extract_action_and_status(stack)
        check = [
            self.status == self.STATUS_IN_PROGRESS,
            self.action != self.expect_action]
        if self.expect_action == self.ACTION_UPDATE:
            check.append(self.stack.updated_time == stack.updated_time)
        return any(check)

    @property
    def is_fail(self):
        return self.status == self.STATUS_FAIL

    @property
    def is_in_progress(self):
        return self.status == self.STATUS_IN_PROGRESS

    @staticmethod
    def _extract_action_and_status(stack):
        try:
            action, status = stack.stack_status.split('_', 1)
        except ValueError:
            raise exc.HEATIntegrationError(
                details='Invalid value in stack.stack_status: {!r}'.format(
                    stack.stack_status))
        return action, status
