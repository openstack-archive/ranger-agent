# -*- coding:utf-8 -*-
# Copyright (c) 2012 OpenStack Foundation
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import sys
import time
import uuid

from werkzeug import exceptions as exc
from werkzeug import routing
from werkzeug import serving
from werkzeug import wrappers


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('bind_port', type=int,
                      help='Port number to bind to')
    argp.add_argument('--bind-address', default='127.0.0.1',
                      help='Address to bind to')
    argp.add_argument('--debug', default=False, action='store_true',
                      help='Enable debugging')

    app_args = argp.parse_args()

    app = _WSGIApplication()

    serving.run_simple(
        app_args.bind_address, app_args.bind_port, app,
        use_debugger=app_args.debug, use_reloader=app_args.debug)


class _CatcherStorage(object):
    def __init__(self, stale_tout=3600):
        self.stale_tout = stale_tout
        self.data = list()

    def add(self, payload):
        self.data.append({
            'time': time.time(),
            'idnr': str(uuid.uuid1()),
            'payload': payload})

    def lookup(self, since=None):
        sidx = self._lookup_slice(since=since)[0]
        if sidx:
            sidx += 1  # skip "last" entity
        return self.data[sidx:]

    def delete(self, since=None, till=None):
        if not self.data:
            return
        sidx, eidx = self._lookup_slice(since, till)
        self.data[sidx:eidx] = []

    def delete_entity(self, idnr):
        for idx, entity in enumerate(self.data):
            if entity['idnr'] != idnr:
                continue
            break
        else:
            raise ValueError('Entity not found')

        self.data.pop(idx)

    def _lookup_slice(self, since=None, till=None):
        sidx = 0
        eidx = None
        if since:
            for idx, entity in enumerate(self.data):
                if entity['idnr'] != since:
                    continue
                sidx = idx
                break

        if till:
            for idx in xrange(len(self.data) - 1, sidx - 1, -1):
                entity = self.data[idx]
                if entity['idnr'] != till:
                    continue
                eidx = idx + 1
                break
        return sidx, eidx

    def _remove_staled(self):
        stale_line = time.time()
        stale_line -= min(stale_line, self.stale_tout)

        for idx, entity in enumerate(self.data):
            if entity['time'] < stale_line:
                continue
            break
        else:
            idx = 0

        self.data[:idx] = []


class _HandlerBase(object):
    def __init__(self, request, path_args):
        self.request = request
        self.path_args = path_args

    def __call__(self):
        raise NotImplementedError


class _NotifierCatcher(_HandlerBase):
    def __call__(self):
        storage.add(self._fetch_payload())
        return {'op': True}

    def _fetch_payload(self):
        if self.request.content_type == 'application/json':
            return self._payload_from_json()
        return self._payload_from_form()

    def _payload_from_json(self):
        try:
            payload = json.loads(self.request.data)
        except (ValueError, TypeError) as e:
            raise exc.BadRequest('Invalid payload: {}'.format(e))
        return payload

    def _payload_from_form(self):
        payload = dict(self.request.form)

        # FIXME: ugly fix of incorrect data transfer from ORD-API
        if len(payload) != 1:
            return payload

        key = payload.keys()[0]
        value = payload[key]
        if value != ['']:
            return payload

        try:
            payload = json.loads(key)
        except (TypeError, ValueError):
            pass
        return payload


class _NotificationsBase(_HandlerBase):
    pass


class _NotificationsList(_NotificationsBase):
    def __call__(self):
        last = self.request.args.get('last')
        payload = storage.lookup(since=last)
        return {
            'notifications': payload}


class _NotificationsDelete(_NotificationsBase):
    def __call__(self):
        since = self.request.args.get('start')
        till = self.request.args.get('end')
        storage.delete(since, till)
        return {'op': True}


class _NotificationsEntityDelete(_NotificationsBase):
    def __call__(self):
        try:
            storage.delete_entity(self.path_args['idnr'])
        except ValueError:
            raise exc.NotFound
        return {'op': True}


class _WSGIApplication(object):
    url_map = routing.Map([
        routing.Rule('/ord-target', endpoint='target', methods=['post']),
        routing.Rule('/api/notifications', methods=['get'],
                     endpoint='api_notify:list'),
        routing.Rule('/api/notifications', methods=['delete'],
                     endpoint='api_notify:remove'),
        routing.Rule('/api/notifications/<idnr>', methods=['delete'],
                     endpoint='api_notify-entity:remove')])

    endpoint_map = {
        'target': _NotifierCatcher,
        'api_notify:list': _NotificationsList,
        'api_notify:remove': _NotificationsDelete,
        'api_notify-entity:remove': _NotificationsEntityDelete}

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, args = adapter.match()
            endpoint = self.endpoint_map[endpoint]

            view = endpoint(request, args)
            payload = view()
            payload = json.dumps(payload)

            response = wrappers.Response(payload, mimetype='application/json')
        except exc.HTTPException as e:
            return e
        return response

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        request = wrappers.Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)


storage = _CatcherStorage()


if __name__ == '__main__':
    sys.exit(main())
