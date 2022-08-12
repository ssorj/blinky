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
import json as _json
import logging as _logging
import os as _os
import re as _re
import struct as _struct
import traceback as _traceback
import urllib as _urllib

_log = _logging.getLogger("brbn")

class Server:
    def __init__(self, app, host="", port=8080, csp="default-src 'self'"):
        self.app = app
        self.host = host
        self.port = port
        self.csp = csp

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
        import uvicorn

        uvicorn.run(self, host=self.host, port=self.port, log_level="error")

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
                await route.resource(self, scope, receive, send)
                return

        await Request(self, scope, receive, send).respond(404, b"Not found")

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
    def __init__(self, app, methods=("GET", "HEAD", "POST")):
        self.app = app
        self.methods = methods

    async def __call__(self, server, scope, receive, send):
        request = Request(server, scope, receive, send)

        try:
            await self.handle(request)
        except Exception as e:
            _log.exception(e)
            trace = _traceback.format_exc()
            await request.respond(500, trace.encode("utf-8"))

    async def handle(self, request):
        if request.method not in self.methods:
            await request.respond(400, b"Bad request: Illegal method")
            return

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

        assert isinstance(content, str)
        assert isinstance(content_type, str)

        await request.respond(200, content.encode("utf-8"), content_type=content_type, etag=server_etag)

    async def process(self, request):
        return None

    async def get_etag(self, request, entity):
        return None

    async def get_content_type(self, request, entity):
        return None

    async def render(self, request, entity):
        return None

class Request:
    def __init__(self, server, scope, receive, send):
        self._server = server
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

    async def get_body(self):
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
        return _json.loads(self.get_body())

    async def respond(self, code, content, content_type=None, etag=None):
        assert isinstance(code, int), type(code)
        assert isinstance(content, bytes), type(content)
        assert content_type is None or isinstance(content_type, str), type(content_type)
        assert etag is None or isinstance(etag, str), type(etag)

        headers = [
            (b"content-security-policy", self._server.csp.encode("utf-8")),
            (b"referrer-policy", b"no-referrer"),
            (b"x-content-type-options", b"nosniff"),
        ]

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

_content_types_by_extension = {
    ".css": "text/css;charset=UTF-8",
    ".html": "text/html;charset=UTF-8",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript;charset=UTF-8",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain;charset=UTF-8",
    ".woff": "application/font-woff",
}

class FileResource(Resource):
    def __init__(self, app, static_dir, subpath=None):
        super().__init__(app, methods=("GET", "HEAD"))

        assert _os.path.isdir(static_dir), static_dir

        self.static_dir = static_dir
        self.subpath = subpath

    async def handle(self, request):
        try:
            await super().handle(request)
        except FileNotFoundError:
            await request.respond(404, b"Not found")

    async def process(self, request):
        subpath = request.get("subpath", self.subpath)

        assert subpath is not None
        assert subpath.startswith("/"), subpath

        return _os.path.join(self.static_dir, subpath[1:])

    async def get_etag(self, request, fs_path):
        mtime = _os.path.getmtime(fs_path)
        return _struct.pack("f", mtime).hex()

    async def get_content_type(self, request, fs_path):
        _, ext = _os.path.splitext(fs_path)
        return _content_types_by_extension.get(ext, "text/plain;charset=UTF-8")

    async def render(self, request, fs_path):
        with open(fs_path, "r") as file:
            return file.read()
