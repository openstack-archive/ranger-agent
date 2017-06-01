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

from heatclient import client as heat
from glanceclient import client as glance
from keystoneclient import discover as keystone_discover
from keystoneclient.v2_0 import client as keystone_v2
from keystoneclient.v3 import client as keystone_v3
from oslo_config import cfg

from ord.openstack.common import log as logging


# FIXME(db2242): we definetly must change this group name. It very confusing.
OPT_GROUP = cfg.OptGroup(name='ord_credentials', title='ORD Credentials')
SERVICE_OPTS = [
    cfg.StrOpt('project_id', default='',
               help="project id used by ranger-agent "
                    "driver of service vm extension"),
    cfg.StrOpt('auth_url', default='http://0.0.0.0:5000/v2.0',
               help="auth URL used by ranger-agent "
                    "driver of service vm extension"),
    cfg.StrOpt('user_name', default='',
               help="user name used by ranger-agent "
                    "driver of service vm extension"),
    cfg.StrOpt('password', default='',
               help="password used by ranger-agent "
                    "driver of service vm extension"),
    cfg.StrOpt('tenant_name', default='',
               help="tenant name used by ranger-agent driver of service vm "
               "extension"),
    cfg.FloatOpt("openstack_client_http_timeout", default=180.0,
                 help="HTTP timeout for any of OpenStack service in seconds"),
    cfg.BoolOpt("https_insecure", default=False,
                help="Use SSL for all OpenStack API interfaces"),
    cfg.StrOpt("https_cacert", default=None,
               help="Path to CA server certificate for SSL")
]

cfg.CONF.register_opts(SERVICE_OPTS, OPT_GROUP)
CONF = cfg.CONF.ord_credentials

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
    discover = keystone_discover.Discover(auth_url=args['auth_url'])
    for version_data in discover.version_data():
        version = version_data['version']
        if version[0] <= 2:
            return keystone_v2.Client(**args)
        elif version[0] == 3:
            return keystone_v3.Client(**args)


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
            'username': CONF.user_name,
            'password': CONF.password,
            'auth_url': CONF.auth_url,
        }

        if CONF.project_id:
            params['tenant_id'] = CONF.project_id
        else:
            params['tenant_name'] = CONF.tenant_name
        client = create_keystone_client(params)
        if client.auth_ref is None:
            client.authenticate()
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
                heat_api_url = kc.service_catalog.url_for(
                    service_type='orchestration')
                auth_token = kc.auth_token
                timeout = CONF.openstack_client_http_timeout
                client = heat.Client(version,
                                     endpoint=heat_api_url,
                                     token=auth_token,
                                     timeout=timeout,
                                     insecure=CONF.https_insecure,
                                     cacert=CONF.https_cacert)
                return client, kc
            except Exception:
                kc = self.keystone()
                attempt = attempt - 1

    @cached
    def glance(self, kc, version='2'):
        """Returns glance client for given version

        @param version: string that specifies the GLANCE API version
        @return glanceclient.client.Client
        """
        attempt = 1
        while attempt >= 0:
            try:
                glance_api_url = kc.service_catalog.url_for(
                    service_type='image')
                auth_token = kc.auth_token
                timeout = CONF.openstack_client_http_timeout
                client = glance.Client(version,
                                       endpoint=glance_api_url,
                                       token=auth_token,
                                       timeout=timeout,
                                       insecure=CONF.https_insecure,
                                       cacert=CONF.https_cacert)
                return client, kc
            except Exception:
                kc = self.keystone()
                attempt = attempt - 1
