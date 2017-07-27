# -*- encoding: utf-8 -*-
#
# Copyright 2014 OpenStack Foundation
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

from ord.db import migration as mig
from ord import service


def sync(version=None):
    service.prepare_service()
    """Sync the database up to the most recent version."""
    return mig.db_sync(version, database='ord')


def dbsync():
    service.prepare_service()
    """Sync the database up to the most recent version."""
    return mig.db_sync(version=None, database='ord')


def version():
    service.prepare_service()
    """Print the current database version."""
    print(mig.db_version(database='ord'))
