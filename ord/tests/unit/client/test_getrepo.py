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

import mock
from mock import patch
import os

from ord.client import getrepo
from ord.common.exceptions import ORDException
from ord.tests import base
from oslo_config import cfg

CONF = cfg.CONF


class GetRepoTestCase(base.BaseTestCase):

    def setUp(self):
        super(GetRepoTestCase, self).setUp()
        self.git_inst = None
        self.local_repo = 'ord_test'
        with patch.object(getrepo.TemplateRepoClient, 'git_init_repo'):
            self.git_inst = getrepo.TemplateRepoClient(self.local_repo)

    def test_pullrepo_template(self):
        path = os.path.abspath('')
        testfile = 'ord/dummy.py'
        expected = path + "/" + testfile
        with patch.object(self.git_inst, 'run_git'):
            result = self.git_inst.pull_template(path, testfile)
        self.assertEqual(expected, result)

    def test_fail_pull_template(self):
        path = os.path.abspath('')
        testfile = 'tests/files/stack0.yaml'
        self.assertRaises(ORDException, self.git_inst.pull_template,
                          path, testfile)

    def test_git_init_repo(self):
        self.subprocess = mock.Mock()
        with patch.object(self.git_inst, 'run_git') as mock_method:
            self.git_inst.git_init_repo(self.local_repo)
        mock_method.assert_called()
