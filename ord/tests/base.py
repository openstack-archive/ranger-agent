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

import os
import tempfile

import mock
import testtools


class BaseTestCase(testtools.TestCase):
    _patches = []

    def __init__(self, *args, **kwargs):
        super(BaseTestCase, self).__init__(*args, **kwargs)
        self._patches = []

    def setUp(self):
        super(BaseTestCase, self).setUp()

        self._patches[:] = []

    def patch(self, *args, **kwargs):
        self._patches.append(mock.patch(*args, **kwargs))
        self.addCleanup(self._patches[-1].stop)
        return self._patches[-1].start()

    @staticmethod
    def make_tempfile(payload=None, prefix=None, named=True):
        if named:
            cls = tempfile.NamedTemporaryFile
        else:
            cls = tempfile.TemporaryFile

        if prefix:
            prefix = 'ord-{}-'.format(prefix)
        else:
            prefix = 'ord-'

        fd = cls(prefix=prefix)
        if payload:
            fd.write(payload)
            fd.seek(0, os.SEEK_SET)

        return fd


class Dummy(object):
    def __init__(self, **attributes):
        self.__dict__.update(attributes)
