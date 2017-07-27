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
"""
SQLAlchemy models for ranger-agent data.
"""

import datetime
import uuid

from sqlalchemy import (Column, DateTime, String)
from sqlalchemy import ForeignKey, Text
from sqlalchemy import orm

from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.declarative import declarative_base

from oslo_config import cfg
from oslo_db.sqlalchemy import models


CONF = cfg.CONF
BASE = declarative_base()


def MediumText():
    return Text().with_variant(MEDIUMTEXT(), 'mysql')


class ORDBase(models.ModelBase):
    metadata = None

    def __copy__(self):
        """Implement a safe copy.copy().

        SQLAlchemy-mapped objects travel with an object
        called an InstanceState, which is pegged to that object
        specifically and tracks everything about that object.  It's
        critical within all attribute operations, including gets
        and deferred loading.   This object definitely cannot be
        shared among two instances, and must be handled.

        The copy routine here makes use of session.merge() which
        already essentially implements a "copy" style of operation,
        which produces a new instance with a new InstanceState and copies
        all the data along mapped attributes without using any SQL.

        The mode we are using here has the caveat that the given object
        must be "clean", e.g. that it has no database-loaded state
        that has been updated and not flushed.   This is a good thing,
        as creating a copy of an object including non-flushed, pending
        database state is probably not a good idea; neither represents
        what the actual row looks like, and only one should be flushed.

        """
        session = orm.Session()

        copy = session.merge(self, load=False)
        session.expunge(copy)
        return copy

    def save(self, session=None):
        from ord.db.sqlalchemy import api

        if session is None:
            session = api.get_session()

        super(ORDBase, self).save(session=session)

    def __repr__(self):
        """sqlalchemy based automatic __repr__ method."""
        items = ['%s=%r' % (col.name, getattr(self, col.name))
                 for col in self.__table__.columns]
        return "<%s.%s[object at %x] {%s}>" % (self.__class__.__module__,
                                               self.__class__.__name__,
                                               id(self), ', '.join(items))


class Ord_Notification(BASE, ORDBase):
    __tablename__ = 'ord_notification'

    request_id = Column(String(50), primary_key=True, nullable=False)
    resource_id = Column(String(80))
    template_type = Column(String(50), default='hot')
    resource_operation = Column(String(20))
    region = Column(String(32))
    time_stamp = Column(DateTime(timezone=False),
                        default=datetime.datetime.now())


class Target_Resource(BASE, ORDBase):
    __tablename__ = 'target_resource'

    template_status_id = Column(String(50),
                                primary_key=True,
                                default=lambda: str(uuid.uuid4()))
    request_id = Column(String(50),
                        ForeignKey('ord_notification.request_id'),
                        nullable=False)
    resource_template_version = Column(String(50), nullable=False)
    resource_name = Column(String(80), nullable=False)
    resource_type = Column(String(50))
    status = Column(String(32))
    error_code = Column(String(32))
    error_msg = Column(String(255))
