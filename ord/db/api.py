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

"""Defines interface for DB access.

Functions in this module are imported into the ranger-agent.db namespace.
Call these functions from ranger-agent.db namespace, not the
ranger-agent.db.api namespace.

All functions in this module return objects that implement a dictionary-like
interface. Currently, many of these objects are sqlalchemy objects that
implement a dictionary interface. However, a future goal is to have all of
these objects be simple dictionaries.

"""

from oslo_config import cfg
from oslo_db import concurrency
from oslo_log import log as logging


CONF = cfg.CONF

_BACKEND_MAPPING = {'sqlalchemy': 'ord.db.sqlalchemy.api'}


IMPL = concurrency.TpoolDbapiWrapper(CONF, backend_mapping=_BACKEND_MAPPING)

LOG = logging.getLogger(__name__)


def create_template(*values):
    return IMPL.create_template(*values)


def retrieve_template(request_id):
    return IMPL.retrieve_template(request_id)


def retrieve_target(request_id):
    return IMPL.retrieve_target(request_id)


def retrieve_target_by_status(template_status_id):
    return IMPL.retrieve_target(template_status_id)


def update_target_data(template_status_id, status,
                       error_code, error_msg):
    return IMPL.update_target_data(template_status_id, status,
                                   error_code, error_msg)
