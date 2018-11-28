# Copyright (c) 2012 OpenStack Foundation
# All Rights Reserved.
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

from ord.client import rpcapi
from ord.common import exceptions as exc
from ord.common import utils
from ord.common.utils import ErrorCode
from ord.db import api as db_api
from ord.i18n import _
from ord.openstack.common import log
from oslo_config import cfg
from pecan import expose
from urllib2 import HTTPError

import datetime
import json
import oslo_messaging as messaging
import urllib2
import uuid
import webob
import webob.exc

LOG = log.getLogger(__name__)

CONF = cfg.CONF
orm_opts = [
    cfg.StrOpt('rds_listener_endpoint',
               help='Endpoint to rds_listener ')

]

opts = [
    cfg.StrOpt('region',
               help='Region')
]

CONF.register_opts(opts)

opt_group = cfg.OptGroup(name='orm',
                         title='Options for the orm service')
CONF.register_group(opt_group)
CONF.register_opts(orm_opts, opt_group)


class ListenerQueueHandler(object):

    def __init__(self):
        super(ListenerQueueHandler, self).__init__()

    def invoke_listener_rpc(self, ctxt, payload):
        LOG.debug(" ----- message from Engine -----")
        LOG.debug(" Payload: %s \n ctxt: %s " % (str(payload), str(ctxt)))
        LOG.debug(" -------------------------------")
        listener_response_body = {}
        try:
            listener_response_body = json.loads(payload)
            LOG.debug(" Payload to RDS Listener %s " % listener_response_body)
            headers = {'Content-type': 'application/json'}
            rds_url = CONF.orm.rds_listener_endpoint
            req = urllib2.Request(rds_url,
                                  json.dumps(listener_response_body),
                                  headers,
                                  unverifiable=False)
            args = {}
            template_status_id = None
            if 'rds-listener' in listener_response_body:
                error_code = (listener_response_body['rds-listener']
                              ['error-code'])
                error_msg = (listener_response_body['rds-listener']
                             ['error-msg'])
                args['error_msg'] = error_msg
                args['error_code'] = error_code
                template_status_id = (listener_response_body['rds-listener']
                                      ['ord-notifier-id'])
            status_code = None
            try:
                LOG.info('Connecting to RDS at %s' % rds_url)
                resp = urllib2.urlopen(req)
                status = utils.STATUS_RDS_SUCCESS
                if resp is not None:
                    status_code = resp.getcode()
            except (HTTPError, Exception) as e:
                status = utils.STATUS_RDS_ERROR
                if "getcode" in dir(e):
                    status_code = e.getcode()
                raise exc.RDSListenerHTTPError(error_msg=error_msg,
                                               error_code=error_code)
        except ValueError as e:
            status = utils.STATUS_RDS_ERROR
            LOG.error('Error while parsing input payload %r', e)
        except Exception as ex:
            status = utils.STATUS_RDS_ERROR
            LOG.error('Error while calling RDS Listener %r', ex)
        finally:
            LOG.info('RDS Listener status %s ' % status)
            LOG.info('RDS Listener status code %s ' % status_code)
            db_api.update_target_data(template_status_id, status, **args)


class NotifierController(object):

    def __init__(self):
        super(NotifierController, self).__init__()
        self._rpcapi = rpcapi.RpcAPI()

    def _prepare_response_message(self, kwargs, target_data,
                                  status, error_msg=None, error_code=None):
        LOG.debug("Create response body with status %s  \
                    code %s " % (status, error_code))
        LOG.debug("message-body %r " % kwargs)
        response_body = kwargs
        response_body['status'] = status
        if error_code is not None:
            response_body['error_msg'] = error_msg
            response_body['error_code'] = error_code

        return response_body

    def _validate_request(self, kwargs):
        error_code = None
        error_msg = None
        template = db_api.retrieve_template(kwargs['request_id'])
        LOG.debug('Template  from DB Call %r ' % template)
        template_target = None
        if template is not None:
            template_target = db_api.retrieve_target(kwargs['request_id'])
            LOG.debug('Template target  from DB Call %r ' % template_target)

        if template is not None:
            if template_target['status'] == \
                    utils.STATUS_SUBMITTED:
                error_code = ErrorCode.ORD_002.value
                error_msg = ErrorCode.tostring(error_code)
            elif kwargs.get('resource-template-name') == \
                template_target.get('resource_template_name') and \
                (template_target.get('status') == utils.STATUS_SUBMITTED or
                 template_target.get('resource_operation') ==
                 kwargs.get('resource-operation')):
                error_code = ErrorCode.ORD_001.value
                error_msg = ErrorCode.tostring(error_code)

        return error_code, error_msg

    def _persist_notification_record(self, kwargs):
        LOG.debug("Persist Template record to database")
        kwargs['time_stamp'] = str(datetime.datetime.now())
        error_code, error_msg = self._validate_request(kwargs)
        if error_code is not None:
            response = self._prepare_response_message(kwargs,
                                                      kwargs,
                                                      status='Not Submitted',
                                                      error_msg=error_msg,
                                                      error_code=error_code)
            return response
        db_api.create_template(kwargs)
        response = self._prepare_response_message(kwargs,
                                                  kwargs,
                                                  status='Submitted')
        return response

    def _validate_input_request(self, payload):
        for key in payload:
            if " " in payload.get(key):
                LOG.debug('Input payload contain white spaces %s' %
                          str(payload))
                msg = _('%s contains white spaces') % key
                raise webob.exc.HTTPBadRequest(explanation=msg)

    @expose(generic=True)
    def ord_notifier(self, **args):
        raise webob.exc.HTTPNotFound

    @ord_notifier.when(method='GET', template='json')
    def ord_notifier_status(self, **vals):
        template_id = vals.get('Id')
        payload = {}
        LOG.debug('Request for check Status by Id %s ' % template_id)
        template = db_api.retrieve_template(template_id)
        if template is not None:
            template_target = db_api.retrieve_target(template_id)
        payload = utils.create_rds_payload(template, template_target)
        LOG.debug('Payload for check Status by Id:%s  is:%s'
                  % (template_id, payload))
        return payload

    @ord_notifier.when(method='POST', template='json')
    def ord_notifier_POST(self, **vals):
        vals = vals['ord-notifier']
        request_id = vals.get('request-id')
        if request_id is None:
            msg = _("A valid request_id parameter is required")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        # FIXME we don't process this field. So why for it here?
        resource_type = vals.get('resource-type')
        if resource_type is None:
            msg = _("A valid resource_type parameter is required")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        # FIXME we support specific set of operation. We must check
        # that received operation is in support list.
        resource_operation = vals.get('operation')
        if resource_operation is None:
            msg = _("A valid resource_operation parameter is required")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        resource_name = vals.get('resource-template-name')
        if resource_name is None:
            msg = _("A valid resource-template-name parameter is required")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        # FIXME: why is this needed?
        template_version = vals.get('resource-template-version')

        # FIXME: we can handle only 'hot' or 'ansible' values here
        # Everything else must be rejected here.
        template_type = vals.get('resource-template-type')
        if template_type is None:
            template_type = utils.TEMPLATE_TYPE_HEAT

        status_id = str(uuid.uuid4())

        region = vals.get('region')
        if region is None:
            msg = _("A valid region is required")
            raise webob.exc.HTTPBadRequest(explanation=msg)
        elif region != CONF.region:
            msg = _("Invalid region specified")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        resource_id = ''
        if 'resource-id' in vals:
            resource_id = vals.get('resource-id')

        kwargs = {
            'request_id': str(request_id),
            'resource_id': resource_id,
            'template_type': template_type,
            'resource_operation': resource_operation,
            'resource_name': resource_name,
            'resource_type': resource_type,
            'resource_template_version': template_version,
            'template_status_id': status_id,
            'status': utils.STATUS_SUBMITTED,
            'region': region
        }

        self._validate_input_request(kwargs)
        LOG.debug('Payload to DB call %r ' % kwargs)
        db_response = self._persist_notification_record(kwargs=kwargs)
        response = {}
        vals['status'] = db_response['status']
        if 'error_code' in db_response:
            vals['error-code'] = db_response['error_code']
            vals['error-msg'] = db_response['error_msg']
        response['ord-notifier-response'] = vals
        if 'error_code' not in db_response:
            LOG.debug("----- message to Engine -----")
            LOG.debug(" message: %s \nstatus_id: %s" %
                      (str(kwargs), str(status_id)))
            LOG.debug("-----------------------------")
            payload = str(kwargs)
            try:
                ctxt = {'request_id': kwargs.get('request_id')}
                self._rpcapi.invoke_notifier_rpc(ctxt, payload)
            except messaging.MessageDeliveryFailure:
                LOG.error("Fail to deliver message")
        else:
            LOG.debug("Template submission to DB failed with %s "
                      % db_response['error_msg'])
            LOG.debug("Message to engine is not triggered")

        return response
