#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import asyncio as _asyncio
import hypercorn as _hypercorn
import hypercorn.asyncio as _hypercorn_asyncio
import json as _json
import logging as _logging
import os as _os
import re as _re
import traceback as _traceback
import urllib as _urllib

_log = _logging.getLogger("brbn")

class Server:
    def __init__(self, app, host="", port=8080):
        self.app = app
        self.host = host
        self.port = port

        self._startup_coros = list()
        self._shutdown_coros = list()
        self._routes = list()

    def add_startup_task(self, coro):
        self._startup_coros.append(coro)

    def add_shutdown_task(self, coro):
        self._shutdown_coros.append(coro)

    def add_route(self, path, resource):
        _log.info(f"Adding route: {path} -> {resource}")

        assert path.startswith("/"), path
        assert path == "/" or not path.endswith("/"), path

        self._routes.append(_Route(path, resource))

    def run(self):
        config = _hypercorn.Config()
        config.bind = [f"{self.host}:{self.port}"]
        config.certfile = "/home/jross/code/certifiable/build/server-cert.pem"
        config.keyfile = "/home/jross/code/certifiable/build/server-key.pem"

        _asyncio.run(_hypercorn_asyncio.serve(self, config))

    async def __call__(self, scope, receive, send):
        type = scope["type"]

        if type == "http":
            await self._handle_http_event(scope, receive, send)
        elif type == "lifespan":
            await self._handle_lifespan_event(scope, receive, send)
        else:
            assert False, type

    async def _handle_http_event(self, scope, receive, send):
        path = scope["path"]

        for route in self._routes:
            match = route.regex.fullmatch(path)

            if match is not None:
                scope["brbn.path_params"] = match.groupdict()
                await route.resource(scope, receive, send)
                return

        await Request(scope, receive, send).respond(404, b"Not found")

    async def _handle_lifespan_event(self, scope, receive, send):
        message = await receive()
        type = message["type"]

        if type == "lifespan.startup":
            for coro in self._startup_coros:
                _asyncio.get_event_loop().create_task(coro)

            await send({"type": "lifespan.startup.complete"})
        elif type == "lifespan.shutdown":
            for coro in self._shutdown_coros:
                _asyncio.get_event_loop().create_task(coro)

            await send({"type": "lifespan.shutdown.complete"})
            return
        else:
            assert False, type

class _Route:
    def __init__(self, path, resource):
        self.path = path
        self.resource = resource

        regex = _re.sub(r"/\*$", r"(?P<subpath>.*)", path)
        regex = _re.sub(r"{(\w+)}", r"(?P<\1>[^/]+)", regex)

        self.regex = _re.compile(regex)

class Resource:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        request = Request(scope, receive, send)

        try:
            await self.handle(request)
        except Exception as e:
            _log.exception(e)
            trace = _traceback.format_exc()
            await request.respond(500, trace.encode("utf-8"))

    async def handle(self, request):
        entity = await self.process(request)
        server_etag = await self.get_etag(request, entity)

        if server_etag is not None:
            server_etag = f'"{server_etag}"'
            client_etag = request.get_header("if-none-match")

            if client_etag == server_etag:
                await request.respond(304, b"")
                return

        if request.method == "HEAD":
            await request.respond(200, b"", etag=server_etag)
            return

        content = await self.render(request, entity)
        content_type = await self.get_content_type(request, entity)

        await request.respond(200, content, content_type=content_type, etag=server_etag)

    async def process(self, request):
        return None

    async def get_etag(self, request, entity):
        return None

    async def get_content_type(self, request, entity):
        return None

    async def render(self, request, entity):
        return None

class ResourceException(Exception):
    pass

class Redirect(ResourceException):
    pass

class BadRequestError(ResourceException):
    pass

class Request:
    def __init__(self, scope, receive, send):
        self._scope = scope
        self._receive = receive
        self._send = send
        self._params = scope["brbn.path_params"]

        query_string = scope["query_string"].decode("utf-8")

        for name, value in _urllib.parse.parse_qsl(query_string):
            self._params[name] = value

    @property
    def method(self):
        return self._scope["method"]

    @property
    def path(self):
        return self._scope["path"]

    def get(self, name, default=None):
        return self._params.get(name, default)

    def require(self, name):
        try:
            return self._params[name]
        except KeyError:
            raise BadRequestError(f"Required parameter not found: {name}")

    def get_header(self, name):
        name = name.encode("utf-8").lower()

        for header_name, header_value in self._scope["headers"]:
            if header_name.lower() == name:
                return header_value.decode("utf-8")

    async def get_content(self) -> bytes:
        message = await self._receive()
        type = message["type"]

        if type == "http.request":
            assert message.get("more_body") in (None, False) # XXX Need to handle streamed data

            return message.get("body", b"")
        elif type == "http.disconnect":
            assert False # XXX Need a disconnect exception
        else:
            assert False

    async def parse_json(self) -> object:
        return _json.loads(self.get_content())

    async def respond(self, code, content, content_type=None, etag=None):
        assert isinstance(code, int), type(code)
        assert isinstance(content, bytes), type(content)
        assert content_type is None or isinstance(content_type, str), type(content_type)
        assert etag is None or isinstance(etag, str), type(etag)

        headers = list()

        if content_type is not None:
            headers.append((b"content-type", content_type.encode("utf-8")))

        if etag is not None:
            headers.append((b"etag", etag.encode("utf-8")))

        start_message = {
            "type": "http.response.start",
            "status": code,
            "headers": headers,
        }

        body_message = {
            "type": "http.response.body",
            "body": content,
            "more_body": False,
        }

        await self._send(start_message)
        await self._send(body_message)

class FileResource(Resource):
    async def receive_request(self, request):
        try:
            await super().receive_request(request)
        except FileNotFoundError:
            await request.respond(404, b"Not found")

    async def process(self, request):
        return _os.path.join(self.app.static_dir, request.get("subpath")[1:]) # XXX This won't work with an exact match

    async def get_etag(self, request, fs_path):
        return _os.path.getmtime(fs_path)

    async def get_content_type(self, request, fs_path):
        if fs_path.endswith(".css"):
            return "text/css;charset=UTF-8"
        elif fs_path.endswith(".html"):
            return "text/html;charset=UTF-8"
        elif fs_path.endswith(".js"):
            return "text/javascript;charset=UTF-8"
        elif fs_path.endswith(".jpeg"):
            return "image/jpeg"
        elif fs_path.endswith(".png"):
            return "image/png"
        elif fs_path.endswith(".svg"):
            return "image/svg+xml"
        else:
            return "text/plain;charset=UTF-8"

    async def render(self, request, fs_path):
        with open(fs_path, "rb") as file:
            return file.read()
