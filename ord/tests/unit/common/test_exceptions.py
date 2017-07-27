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

from ord.common import exceptions as exc
from ord.tests import base


class TestExceptions(base.BaseTestCase):
    def test_no_argumen_error(self):
        err = _SubjectError0()
        self.assertEqual('Error: subject0', err.message)

    def test_message_override(self):
        err = _SubjectError0('Subject0: fully custom message')
        self.assertEqual('Subject0: fully custom message', err.message)

    def test_argument_substitution(self):
        err = _SubjectError1(sub='runtime substitution')
        self.assertEqual('Error: subject1 - runtime substitution', err.message)

    def test_missing_mandatory_argument(self):
        self.assertRaises(TypeError, _SubjectError1)

    def test_custom_message_and_substitution(self):
        self.assertRaises(TypeError, _SubjectError1,
                          'Custom error message', sub='test')

    def test_default_substitution(self):
        err = _SubjectError2()
        self.assertEqual('Error: subject2 - default description', err.message)

    def test_default_substitution_inheritance(self):
        err = _SubjectError3()
        self.assertEqual('Error: subject3 - default description, one more '
                         'default substitution', err.message)

    def test_substitution_overrride(self):
        err = _SubjectError3(sub='aaa', sub2='bbb')
        self.assertEqual('Error: subject3 - aaa, bbb', err.message)

    def test_arguments(self):
        dummy = base.Dummy(test='test')
        e = _SubjectError2(dummy=dummy)

        self.assertEqual({
            'sub': 'default description',
            'dummy': dummy}, e.arguments)

    def test_arguments_immutability(self):
        e = _SubjectError2()
        e.arguments['sub'] = 'test'
        e.arguments['new'] = 'new'

        self.assertEqual({
            'sub': 'default description'}, e.arguments)

    def test_clone(self):
        dummy = base.Dummy(clone='clone')
        e = _SubjectError2()

        e_cloned = e.clone(sub='clone', dummy=dummy)
        self.assertIs(_SubjectError2, type(e_cloned))
        self.assertEqual({
            'sub': 'clone',
            'dummy': dummy}, e.arguments)
        self.assertEqual('Error: subject2 - clone', e_cloned.message)


class _SubjectError0(exc.ORDException):
    message_template = 'Error: subject0'


class _SubjectError1(exc.ORDException):
    message_template = 'Error: subject1 - {sub}'


class _SubjectError2(exc.ORDException):
    message_template = 'Error: subject2 - {sub}'

    default_substitution_values = {
        'sub': 'default description'}


class _SubjectError3(_SubjectError2):
    message_template = 'Error: subject3 - {sub}, {sub2}'

    default_substitution_values = {
        'sub2': 'one more default substitution'}
