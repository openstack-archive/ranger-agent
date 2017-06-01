# Copyright 2016 ATT
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

import copy
from enum import Enum
import multiprocessing

import six

from ord.common import exceptions as exc

OPERATION_CREATE = 'create'
OPERATION_MODIFY = 'modify'
OPERATION_DELETE = 'delete'

STATUS_SUBMITTED = 'Submitted'
STATUS_ERROR = 'Error'
STATUS_INTERNAL_ERROR = 'Error'
STATUS_SUCCESS = 'Success'
STATUS_RDS_ERROR = 'Error_RDS_Dispatch'
STATUS_RDS_SUCCESS = 'Success_RDS_Dispatch'

TEMPLATE_TYPE_HEAT = 'hot'
TEMPLATE_TYPE_ANSIBLE = 'ansible'

RESOURCE_IMAGE = 'Image'


def load_file(name):
    try:
        fd = open(name, 'rt')
        payload = fd.read()
    except IOError as e:
        raise exc.InternalError(
            'Can\'t load {!r}: {}'.format(e.filename, e.message))
    return payload


def printable_time_interval(delay, show_ms=False):
    suffixes = ['ms', 's', 'm', 'h', 'd']

    chunks = []
    for div in [1, 60, 60, 24]:
        if not delay:
            break
        chunks.append(delay % div)
        delay //= div

    if delay:
        chunks.append(delay)
    if chunks:
        chunks[0] *= 1000
        if not show_ms:
            chunks.pop(0)
            suffixes.pop(0)

    chunks = [int(x) for x in chunks]
    result = ' '.join(reversed(
        ['{}{}'.format(a, b) for a, b in zip(chunks, suffixes)]))
    if not result:
        result = '0ms'

    return result


def cpu_count():
    try:
        return multiprocessing.cpu_count() or 1
    except NotImplementedError:
        return 1


# FIXME(db2242): unused!
def update_nested(original_dict, updates):
    """Updates the leaf nodes in a nest dict.

     Updates occur without replacing entire sub-dicts.
    """
    dict_to_update = copy.deepcopy(original_dict)
    for key, value in six.iteritems(updates):
        if isinstance(value, dict):
            sub_dict = update_nested(dict_to_update.get(key, {}), value)
            dict_to_update[key] = sub_dict
        else:
            dict_to_update[key] = updates[key]
    return dict_to_update


def create_rds_payload(template, template_target):
    resource_id = template.get('resource_id')
    region = template.get('region')
    operation = template.get('resource_operation')
    request_id = template.get('request_id')
    resource_template_type = template.get('template_type')
    resource_type = template_target.get('resource_type')
    template_version = template_target.get('resource_template_version')
    ord_notifier_id = template_target.get('template_status_id')
    status = template_target.get('status')
    error_code = template_target.get('error_code')
    error_msg = template_target.get('error_msg')
    payload = {"rds-listener":
               {"request-id": request_id,
                "resource-id": resource_id,
                "resource-type": resource_type,
                "resource-template-version": template_version,
                "resource-template-type": resource_template_type,
                "resource-operation": operation,
                "ord-notifier-id": ord_notifier_id,
                "region": region,
                "status": status,
                "error-code": error_code,
                "error-msg": error_msg,
                }
               }
    return payload


# FIXME(db2242): remove it
class ErrorCode(Enum):

    ORD_NOERROR = ""
    ORD_000 = "ORD_000"
    ORD_001 = "ORD_001"
    ORD_002 = "ORD_002"
    ORD_003 = "ORD_003"
    ORD_004 = "ORD_004"
    ORD_005 = "ORD_005"
    ORD_006 = "ORD_006"
    ORD_007 = "ORD_007"
    ORD_008 = "ORD_008"
    ORD_009 = "ORD_009"
    ORD_010 = "ORD_010"
    ORD_011 = "ORD_011"
    ORD_012 = "ORD_012"
    ORD_013 = "ORD_013"
    ORD_014 = "ORD_014"
    ORD_015 = "ORD_015"
    ORD_016 = "ORD_016"
    ORD_017 = "ORD_017"
    ORD_018 = "ORD_018"
    ORD_019 = "ORD_019"

    def __getattr__(self, code):
        if code in self:
            return code
        raise AttributeError

    @classmethod
    def tostring(cls, errorCode):
        ord_err = {'ORD_000': 'Stack Creation Failed',
                   'ORD_001': 'Template already exists',
                   'ORD_002': 'Template already submitted and in process',
                   'ORD_003': 'Template submission timed out',
                   'ORD_004': 'Template submission failed',
                   'ORD_005': 'Unable to pull Template',
                   'ORD_006': 'Unsupported operation',
                   'ORD_007': 'Thread not found',
                   'ORD_008': 'Unknown Exception',
                   'ORD_009': 'Stack Modification Failed',
                   'ORD_010': 'Stack Deletion Failed',
                   'ORD_011': 'Not Able to Retrieve Stack Status',
                   'ORD_012': 'Stack not found',
                   'ORD_013': 'Stack Time Out Exception',
                   'ORD_014': 'Template not found',
                   'ORD_015': 'Stack create failed and delete completed',
                   'ORD_016': 'Keystone failed to initialize',
                   'ORD_017': 'Clients failed to initialize',
                   'ORD_018': 'Failed to initialize and download repo',
                   'ORD_019': 'Fail to communicate to message broker',
                   'ORD_NOERROR': ''}
        return dict.get(ord_err, errorCode)
