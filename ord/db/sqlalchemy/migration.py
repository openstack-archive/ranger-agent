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

import os

import sqlalchemy

from migrate import exceptions as versioning_exceptions
from migrate.versioning import api as versioning_api
from migrate.versioning.repository import Repository
from ord.db.sqlalchemy import api as db_session
from oslo_log import log as logging


INIT_VERSION = {}
INIT_VERSION['ord'] = 0
_REPOSITORY = {}

LOG = logging.getLogger(__name__)


def get_engine(database='ord'):
    return db_session.get_engine()


def db_sync(version=None, database='ord'):
    if version is not None:
        try:
            version = int(version)
        except ValueError as exc:
            LOG.exception(exc)
            # raise exception("version should be an integer")

    current_version = db_version(database)
    repository = _find_migrate_repo(database)
    if version is None or version > current_version:
        return versioning_api.upgrade(get_engine(database), repository,
                                      version)
    else:
        return versioning_api.downgrade(get_engine(database), repository,
                                        version)


def db_version(database='ord'):
    repository = _find_migrate_repo(database)
    try:
        return versioning_api.db_version(get_engine(database), repository)
    except versioning_exceptions.DatabaseNotControlledError as exc:
        meta = sqlalchemy.MetaData()
        engine = get_engine(database)
        meta.reflect(bind=engine)
        tables = meta.tables
        if len(tables) == 0:
            db_version_control(INIT_VERSION[database], database)
            return versioning_api.db_version(get_engine(database), repository)
        else:
            LOG.exception(exc)


def db_initial_version(database='ord'):
    return INIT_VERSION[database]


def db_version_control(version=None, database='ord'):
    repository = _find_migrate_repo(database)
    versioning_api.version_control(get_engine(database), repository, version)
    return version


def _find_migrate_repo(database='ord'):
    """Get the path for the migrate repository."""
    global _REPOSITORY
    rel_path = 'migrate_repo'
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                        rel_path)
    assert os.path.exists(path)
    if _REPOSITORY.get(database) is None:
        _REPOSITORY[database] = Repository(path)
    return _REPOSITORY[database]
