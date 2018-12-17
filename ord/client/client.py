# All Rights Reserved.
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

from glanceclient import client as glance
from heatclient import client as heat
from keystoneclient.auth.identity import v3
from keystoneclient import session as ksc_session
from keystoneclient.v3 import client as keystone_v3
from oslo_config import cfg

from ord.common import exceptions as exc
from ord.openstack.common import log as logging

OPT_GROUP = cfg.OptGroup(name='keystone_authtoken',
                         title='Keystone Configurations')
SERVICE_OPTS = [
    cfg.StrOpt('project_name', default='service',
               help="project name  used to stack heat resources"),
    cfg.StrOpt('auth_url', default='',
               help="auth url used by ranger agent to invoke keystone apis"),
    cfg.StrOpt('username', default='',
               help="user name used by ranger agent to invoke keystone apis"),
    cfg.StrOpt('password', default='', secret=True,
               help="password used by ranger agent to invoke keystone apis"),
    cfg.StrOpt('project_domain_name', default='default',
               help="default project domain "
               "used by ranger agent to invoke keystone apis"),
    cfg.StrOpt('auth_version', default='v3', help="Keystone version"),
    cfg.StrOpt("user_domain_name", default='default',
               help="default project domain "
               "used by ranger agent to invoke keystone apis"),
    cfg.StrOpt("https_cacert", default=None,
               help="Path to CA server certificate for SSL"),
]

cfg.CONF.register_opts(SERVICE_OPTS, OPT_GROUP)
CONF = cfg.CONF.keystone_authtoken

LOG = logging.getLogger(__name__)


def cached(func):
    """Cache client handles."""

    def wrapper(self, *args, **kwargs):
        key = '{0}{1}{2}'.format(func.__name__,
                                 str(args) if args else '',
                                 str(kwargs) if kwargs else '')

        if key in self.cache:
            return self.cache[key]
        self.cache[key] = func(self, *args, **kwargs)
        return self.cache[key]

    return wrapper


def create_keystone_client(args):
    auth = v3.Password(auth_url=args['auth_url'],
                       username=args['username'],
                       password=args['password'],
                       project_name=args['project_name'],
                       user_domain_name=args['user_domain_name'],
                       project_domain_name=args['project_domain_name'])
    session = ksc_session.Session(auth=auth)
    return keystone_v3.Client(session=session,
                              auth_url=args['auth_url'],
                              project_name=args['project_name'],
                              username=args['username'],
                              password=args['password'])


class Clients(object):

    def __init__(self):
        self.cache = {}

    def clear(self):
        """Remove all cached client handles."""
        self.cache = {}

    @cached
    def keystone(self):
        """Returns keystone Client."""
        params = {
            'username': CONF.username,
            'password': CONF.password,
            'auth_url': CONF.auth_url,
            'project_name': CONF.project_name,
            'user_domain_name': CONF.user_domain_name,
            'project_domain_name': CONF.project_domain_name,
            'https_cacert': CONF.https_cacert
        }
        try:
            client = create_keystone_client(params)
            if client.auth_ref is None:
                client.authenticate()
        except Exception as e:
            LOG.critical("Failed to initialize Keystone %s ", e)
            raise exc.KeystoneInitializationException(e.message)

        return client

    @cached
    def heat(self, kc, version='1'):
        """Returns heat client for given version

        @param version: string that specifies the HEAT API version
        @return heatclient.client.Client
        """
        attempt = 1
        while attempt >= 0:
            try:
                heat_api_url = kc.session.get_endpoint(
                    service_type='orchestration',
                    interface = 'public')
                auth_token = kc.auth_token
                client = heat.Client(version,
                                     endpoint=heat_api_url,
                                     cacert=CONF.https_cacert,
                                     token=auth_token)
                return client, kc
            except Exception as ex:
                try:
                    kc = self.keystone()
                except Exception as e:
                    LOG.critical("Failed to initialize Keystone %s ", e)
                    raise exc.KeystoneInitializationException(e.message)
                if attempt >= 0:
                    attempt = attempt - 1
                else:
                    LOG.critical("Failed to initialize Heat Client %s ", ex)
                    raise exc.HEATIntegrationError(ex.message)

    @cached
    def glance(self, kc, version='2'):
        """Returns glance client for given version

        @param version: string that specifies the GLANCE API version
        @return glanceclient.client.Client
        """
        attempt = 1
        while attempt >= 0:
            try:
                glance_api_url = kc.session.get_endpoint(
                    service_type='image',
                    interface = 'public')
                auth_token = kc.auth_token
                client = glance.Client(version,
                                       endpoint=glance_api_url,
                                       token=auth_token,
                                       cacert=CONF.https_cacert)
                return client, kc
            except Exception as ex:
                try:
                    kc = self.keystone()
                except Exception as e:
                    LOG.critical("Failed to initialize Keystone %s ", e)
                    raise exc.KeystoneInitializationException(e.message)
                if attempt >= 0:
                    attempt = attempt - 1
                else:
                    LOG.critical("Failed to initialize Client Client %s ", ex)
                    raise exc.HEATIntegrationError(ex.message)
