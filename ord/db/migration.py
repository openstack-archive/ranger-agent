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

"""Database setup and migration commands."""

from ord.db.sqlalchemy import migration

IMPL = migration


def db_sync(version=None, database='ord'):
    """Migrate the database to `version` or the most recent version."""
    return IMPL.db_sync(version=version, database=database)


def db_version(database='ord'):
    """Display the current database version."""
    return IMPL.db_version(database=database)


def db_initial_version(database='ord'):
    """The starting version for the database."""
    return IMPL.db_initial_version(database=database)
