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

import errno
import os

from ord.common import exceptions as exc
from ord.common import utils
from ord.tests import base


class TestUtils(base.BaseTestCase):
    def test_load_file(self):
        payload = 'dummy' * 5

        temp = self.make_tempfile(payload=payload)
        result = utils.load_file(temp.name)

        self.assertEqual(payload, result)

    def test_load_file_fail(self):
        temp = self.make_tempfile(payload='payload')
        error = IOError(errno.ENOENT, os.strerror(errno.ENOENT), temp.name)
        self.patch('__builtin__.open', side_effect=error)

        self.assertRaises(exc.InternalError, utils.load_file, temp.name)

    def test_printable_time_interval(self):
        for delay, expect, expect_no_ms in (
                (0, '0ms', '0ms'),
                (1, '1s 0ms', '1s'),
                (1.50001, '1s 500ms', '1s'),
                (65, '1m 5s 0ms', '1m 5s'),
                (3605, '1h 0m 5s 0ms', '1h 0m 5s'),
                (3601 * 25, '1d 1h 0m 25s 0ms', '1d 1h 0m 25s'),
                (3600 * 24 * 367, '367d 0h 0m 0s 0ms', '367d 0h 0m 0s')):
            self.assertEqual(
                expect, utils.printable_time_interval(delay, show_ms=True))
            self.assertEqual(
                expect_no_ms, utils.printable_time_interval(delay))
