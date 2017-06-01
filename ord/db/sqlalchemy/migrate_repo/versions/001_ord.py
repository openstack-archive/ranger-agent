# Copyright 2012 OpenStack Foundation
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

from oslo_log import log as logging
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import dialects
from sqlalchemy import ForeignKeyConstraint, MetaData, String, Table
from sqlalchemy import Text

LOG = logging.getLogger(__name__)


# Note on the autoincrement flag: this is defaulted for primary key columns
# of integral type, so is no longer set explicitly in such cases.

def MediumText():
    return Text().with_variant(dialects.mysql.MEDIUMTEXT(), 'mysql')


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    ord_notification = Table('ord_notification', meta,
                             Column(
                                 'request_id', String(length=50),
                                 primary_key=True, nullable=False),
                             Column('resource_id', String(length=80)),
                             Column('template_type', String(length=50)),
                             Column('resource_operation', String(length=20)),
                             Column('region', String(length=32)),
                             Column('time_stamp', DateTime(timezone=False)),
                             mysql_engine='InnoDB',
                             mysql_charset='utf8'
                             )

    target_resource = Table('target_resource', meta,
                            Column('template_status_id', String(
                                length=50), primary_key=True, nullable=False),
                            Column('request_id', String(length=50)),
                            Column('resource_template_version',
                                   String(length=50)),
                            Column('resource_name', String(length=80)),
                            Column('resource_type', String(length=50)),
                            Column('status', String(length=32),
                                   nullable=False),
                            Column('error_code', String(length=32)),
                            Column('error_msg', String(length=255)),
                            ForeignKeyConstraint(
                                ['request_id'],
                                ['ord_notification.request_id']),
                            mysql_engine='InnoDB',
                            mysql_charset='utf8'
                            )

    tables = [ord_notification, target_resource]

    for table in tables:
        try:
            table.create()
        except Exception:
            LOG.info(repr(table))
            LOG.exception('Exception while creating table.')
            raise

    if migrate_engine.name == 'mysql':
        # In Folsom we explicitly converted migrate_version to UTF8.
        migrate_engine.execute(
            'ALTER TABLE migrate_version CONVERT TO CHARACTER SET utf8')
        # Set default DB charset to UTF8.
        migrate_engine.execute(
            'ALTER DATABASE %s DEFAULT CHARACTER SET utf8' %
            migrate_engine.url.database)


def downgrade(migrate_engine):
    raise NotImplementedError('Downgrade is not implemented.')
