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

import abc
import six


# ORD/RDS error_codes with description. This error codes used into
# responses/notifications designed for ORM/RDS system.
#
# ORD_000: Stack Creation Failed
# ORD_001: Template already exists  (API)
# ORD_002: Template already submitted and in process  (API)
# ORD_003: Template submission timed out  (unused)
# ORD_004: Template submission failed  (unused)
# ORD_005: Template pull timeout  (unused - removed with timeout logic)
# ORD_006: Unsupported operation  (shared with unsupported template type)
# ORD_007: Thread not found  (unused - never returned to external apps)
# ORD_008: Unknown Exception
# ORD_009: Stack Modification Failed
# ORD_010: Stack Deletion Failed
# ORD_011: Not Able to Retrieve Stack Status (can't be used, covered by
#          other errors)
# ORD_012: Stack not found
# ORD_013: Stack Time Out Exception  (unused - removed with timeout logic)
# ORD_014: Template not found
# ORD_015: Stack create failed and delete completed

SUCCESS_CODE = ''
ERROR_HEAT_STACK_CREATE = 'ORD_000'
ERROR_TEMPLATE_NOT_FOUND = 'ORD_005'
ERROR_UNSUPPORTED_OPERATION = 'ORD_006'
ERROR_UNKNOWN_EXCEPTION = 'ORD_008'
ERROR_HEAT_STACK_UPDATE = 'ORD_009'
ERROR_HEAT_STACK_DELETE = 'ORD_010'
ERROR_HEAT_STACK_LOOKUP = 'ORD_012'
ERROR_TIMEOUT = 'ORD_013'
ERROR_KEYSTONE_INIT = 'ORD_016'
ERROR_CLIENT_INIT = 'ORD_017'
ERROR_REPO_INIT = 'ORD_018'
ERROR_RPC_INIT = 'ORD_019'
ERROR_REPO_TIMEOUT = 'ORD_020'
ERROR_REPO_URL = 'ORD_021'
ERROR_REPO_NOT_EXIST = 'ORD_022'
ERROR_REPO_PERMISSION = 'ORD_023'
ERROR_REPO_UNKNOWN = 'ORD_024'
ERROR_FILE_NOT_IN_REPO = 'ORD_025'

ERROR_STACK_ROLLBACK = 'ORD_015'
ERROR_CODELESS = 'ORD_XXX'


@six.add_metaclass(abc.ABCMeta)
class ORDException(Exception):

    """Base Ord Exception"""

    error_code = ERROR_CODELESS
    default_substitution_values = dict()

    @property
    def message(self):
        return self.args[0]

    @property
    def arguments(self):
        try:
            values = self.args[1]
        except IndexError:
            values = {}
        return values.copy()

    @property
    def substitution_values(self):
        values = dict()
        for cls in reversed(type(self).__mro__):
            try:
                values.update(cls.default_substitution_values)
            except AttributeError:
                pass
        try:
            values.update(self.__dict__['default_substitution_values'])
        except KeyError:
            pass

        return values

    @abc.abstractproperty
    def message_template(self):
        """Force subclasses to define 'message_template' attribute."""

    def __init__(self, *args, **kwargs):
        if args and kwargs:
            raise TypeError(
                'You must not use *args and **kwargs in {!r}'.format(
                    type(self)))
        if args:
            super(ORDException, self).__init__(*args)
            return

        arguments = self.substitution_values
        arguments.update(kwargs)

        try:
            message = self.message_template.format(**arguments)
        except (KeyError, IndexError, AttributeError) as e:
            raise TypeError('Unable to assemble error message. Error: {}. '
                            'Template: {}'.format(e, self.message_template))

        super(ORDException, self).__init__(message, arguments)

    def clone(self, **kwargs):
        try:
            arguments = self.args[1]
        except IndexError:
            arguments = dict()

        arguments.update(kwargs)
        return type(self)(**arguments)


class InternalError(ORDException):
    message_template = 'Internal error'


class IntegrationError(ORDException):
    message_template = ('Error during interaction with external service: '
                        '{details}')
    default_substitution_values = {
        'details': 'there is no details about this error'}


class HEATIntegrationError(IntegrationError):
    message_template = ('Error during interaction with HEAT: '
                        '{action} - {details}')
    default_substitution_values = {
        'action': '(undef)'}


class HEATStackCreateError(HEATIntegrationError):
    error_code = ERROR_HEAT_STACK_CREATE
    default_substitution_values = {
        'action': 'stacks.create'}


class HEATStackUpdateError(HEATIntegrationError):
    error_code = ERROR_HEAT_STACK_UPDATE
    default_substitution_values = {
        'action': 'stacks.update'}


class HEATStackDeleteError(HEATIntegrationError):
    error_code = ERROR_HEAT_STACK_DELETE
    default_substitution_values = {
        'action': 'stacks.delete'}


class HEATLookupError(HEATIntegrationError):
    message_template = 'HEAT {object} not found. Query by {query}'


class HEATStackLookupError(HEATLookupError):
    error_code = ERROR_HEAT_STACK_LOOKUP
    default_substitution_values = {
        'object': 'stack'}


class UnsupportedOperationError(ORDException):
    error_code = ERROR_UNSUPPORTED_OPERATION
    message_template = 'Got unsupported operation {operation!r}'


class UnsupportedTemplateTypeError(UnsupportedOperationError):
    message_template = 'Got unsupported template type {template!r}'


class StackOperationError(ORDException):
    message_template = ('Not able to perform {operation} operation for '
                        '{stack} stack.')


class PullTemplateOperationError(ORDException):
    error_code = ERROR_TEMPLATE_NOT_FOUND
    message_template = 'Failed to fetch template {name}.'


class StackTimeoutError(ORDException):
    error_code = ERROR_TIMEOUT
    message_template = ('Timeout: Not able to perform {operation} operation '
                        'for {stack} stack.')


class WorkerThreadError(ORDException):
    message_template = 'Worker Thread ({thread_id}) was not initiated.'


class StackRollbackError(ORDException):
    error_code = ERROR_STACK_ROLLBACK
    message_template = ('Unable to create stack {error.message}. Rollback '
                        'status: {rollback_status} - {rollback_message}')
    default_substitution_values = {
        'rollback_status': None,
        'rollback_message': None}


class KeystoneInitializationException(ORDException):
    error_code = ERROR_KEYSTONE_INIT
    message_template = 'Keystone authentication failed'


class ClientInitializationException(ORDException):
    error_code = ERROR_CLIENT_INIT
    message_template = 'Failed to initialize Heat'


class RepoTimeoutException(ORDException):
    error_code = ERROR_REPO_TIMEOUT
    message_template = '[{label}] '\
        'Timeout occurred while trying to connect to GIT repo'


class RepoIncorrectURL(ORDException):
    error_code = ERROR_REPO_URL
    message_template = '[{label}] An error occurred with the GIT repo url. ' \
        'Check conf file to confirm URL'


class RepoNotExist(ORDException):
    error_code = ERROR_REPO_NOT_EXIST
    message_template = '[{label}] '\
        'Git repo is incorrect or does not exist'


class FileNotInRepo(ORDException):
    error_code = ERROR_FILE_NOT_IN_REPO
    message_template = '[{label}] '\
        'File does not exist in this Git repo'


class RepoNoPermission(ORDException):
    error_code = ERROR_REPO_PERMISSION
    message_template = '[{label}] '\
        'Permission denied to repo. Check SSH keys'


class RepoUnknownException(ORDException):
    error_code = ERROR_REPO_UNKNOWN
    message_template = '[{label}] '\
        'An unknown repo exception occurred - {unknown}'


class RepoInitializationException(ORDException):
    error_code = ERROR_REPO_INIT
    message_template = 'Failed to connect and download repo'


class RPCInitializationException(ORDException):
    error_code = ERROR_RPC_INIT
    message_template = 'Failed to initialize RPC'


class RDSListenerHTTPError(ORDException):
    message_template = 'RDS listener connection error.'
