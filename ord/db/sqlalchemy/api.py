# Copyright (c) 2012 OpenStack Foundation
# All Rights Reserved.
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

"""Implementation of SQLAlchemy backend."""

import sys
import threading

from ord.db.sqlalchemy import models
from oslo_config import cfg
from oslo_db import options as oslo_db_options
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as sqlalchemyutils
from oslo_log import log as logging

CONF = cfg.CONF

api_db_opts = [
    cfg.StrOpt('connection',
               help='The SQLAlchemy connection string to use to connect to '
                    'the ORD database.',
               secret=True),
    cfg.StrOpt('mysql_sql_mode',
               default='TRADITIONAL',
               help='The SQL mode to be used for MySQL sessions. '
                    'This option, including the default, overrides any '
                    'server-set SQL mode. To use whatever SQL mode '
                    'is set by the server configuration, '
                    'set this to no value. Example: mysql_sql_mode='),
]


opt_group = cfg.OptGroup(name='database',
                         title='Options for the database service')
CONF.register_group(opt_group)
CONF.register_opts(oslo_db_options.database_opts, opt_group)

LOG = logging.getLogger(__name__)

_ENGINE_FACADE = {'ord': None}
_ORD_API_FACADE = 'ord'
_LOCK = threading.Lock()


def _create_facade(conf_group):

    return db_session.EngineFacade(
        sql_connection=conf_group.connection,
        autocommit=True,
        expire_on_commit=False,
        mysql_sql_mode=conf_group.mysql_sql_mode,
        idle_timeout=conf_group.idle_timeout,
        connection_debug=conf_group.connection_debug,
        connection_trace=conf_group.connection_trace,
        max_retries=conf_group.max_retries)


def _create_facade_lazily(facade, conf_group):
    global _LOCK, _ENGINE_FACADE
    if _ENGINE_FACADE[facade] is None:
        with _LOCK:
            if _ENGINE_FACADE[facade] is None:
                _ENGINE_FACADE[facade] = _create_facade(conf_group)
    return _ENGINE_FACADE[facade]


def get_engine(use_slave=False):
    conf_group = CONF.database
    facade = _create_facade_lazily(_ORD_API_FACADE, conf_group)
    return facade.get_engine(use_slave=use_slave)


def get_api_engine():
    conf_group = CONF.database
    facade = _create_facade_lazily(_ORD_API_FACADE, conf_group)
    return facade.get_engine()


def get_session(use_slave=False, **kwargs):
    conf_group = CONF.database
    facade = _create_facade_lazily(_ORD_API_FACADE, conf_group)
    return facade.get_session(use_slave=use_slave, **kwargs)


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def create_template(values):
    LOG.debug('Create Template : %r', values)
    session = get_session()
    with session.begin():
        template_ref = models.Ord_Notification()
        template_ref.update(values)
        template_ref.save(session=session)
        error_code = None
        error_msg = None
        if 'error_code' in values:
            error_code = values['error_code']
            error_msg = values['error_msg']
        set_target_data(template_ref,
                        values['template_status_id'],
                        values['resource_name'],
                        values['resource_type'],
                        values['resource_template_version'],
                        values['status'],
                        error_code,
                        error_msg,
                        session)


def create_target(values, session=None):
    target_ref = models.Target_Resource()
    target_ref.update(values)
    target_ref.save(session=session)


def set_target_data(template_ref, template_status_id,
                    resource_name, resource_type,
                    resource_template_version, status,
                    error_code, error_msg, session):
    values = {'template_status_id': template_status_id,
              'request_id': template_ref.request_id,
              'resource_name': resource_name,
              'resource_template_version': resource_template_version,
              'resource_type': resource_type,
              'status': status,
              'error_code': error_code,
              'error_msg': error_msg}
    create_target(values, session)


def model_query(model,
                args=None,
                session=None):
    """Query helper

    :param model:       Model to query. Must be a subclass of ModelBase.
    :param args:        Arguments to query. If None - model is used.
    :param session:     If present, the session to use.
    """

    if session is None:
        session = get_session()

    query = sqlalchemyutils.model_query(model, session, args)

    return query


def update_target_data(template_status_id, status,
                       error_code=None, error_msg=None):
    LOG.debug('Update status of %s to %s' % (template_status_id, status))

    if error_msg:
        error_msg = error_msg[:255]

    session = get_session()
    with session.begin():
        query = model_query(models.Target_Resource, session=session)
        query = query.filter_by(template_status_id=template_status_id)
        query.update({'status': status,
                      'error_code': error_code,
                      'error_msg': error_msg})


def retrieve_template(request_id):
    LOG.debug('Retrieve Notification By %s', request_id)
    session = get_session()
    query = model_query(models.Ord_Notification, session=session)
    query = query.filter_by(request_id=request_id)

    return query.first()


def retrieve_target_by_status(template_status_id):
    LOG.debug('Retrieve Target data %s by status id', template_status_id)
    session = get_session()
    query = model_query(models.Target_Resource, session=session)
    query = query.filter_by(template_status_id=template_status_id)

    return query.first()


def retrieve_target(request_id):
    LOG.debug('Retrieve Target data %s', request_id)
    session = get_session()
    query = model_query(models.Target_Resource, session=session)
    query = query.filter_by(request_id=request_id)

    return query.first()
