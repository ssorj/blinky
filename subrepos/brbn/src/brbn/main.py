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

import argparse as _argparse
import asyncio as _asyncio
import importlib as _importlib
import inspect as _inspect
import json as _json
import logging as _logging
import os as _os
import re as _re
import struct as _struct
import traceback as _traceback
import urllib as _urllib
import uvicorn as _uvicorn

_log = _logging.getLogger("brbn.main")

class Server:
    def __init__(self):
        self.csp = "default-src 'self'"
        self.started = _asyncio.Event()
        self.stopped = _asyncio.Event()

        self._startup_coros = list()
        self._shutdown_coros = list()
        self._routes = list()

        self._task = None
        self._loop = None

    def __repr__(self):
        return _format_repr(self)

    def add_startup_task(self, coro):
        self._startup_coros.append(coro)

    def add_shutdown_task(self, coro):
        self._shutdown_coros.append(coro)

    def add_route(self, path, resource):
        assert path.startswith("/"), path
        assert path == "/" or not path.endswith("/"), path

        route = _Route(path, resource)
        self._routes.append(route)

        _log.info(f"Route: {route}")

    def run(self, host="", port=8080):
        _asyncio.run(self._run(host=host, port=port))

    async def _run(self, host=None, port=None):
        assert self._task is None, self._task

        self._task = _asyncio.create_task(self._run_uvicorn(host, port))
        self._loop = _asyncio.get_running_loop()

        await self._task

    async def start(self, host=None, port=None):
        assert self._task is None, self._task

        self._task = _asyncio.create_task(self._run_uvicorn(host, port))
        self._loop = _asyncio.get_running_loop()

        await self.started.wait()

    async def stop(self):
        if self._task is None:
            return

        self._task.cancel()

        self._task = None
        self._loop = None

        await self.stopped.wait()

    async def _run_uvicorn(self, host=None, port=None):
        config = _uvicorn.Config(self, host=host, port=port, log_level="info")
        server = _UvicornServer(config, self.started, self.stopped)

        server.config.setup_event_loop()

        try:
            await server.serve()
        except _asyncio.CancelledError:
            await server.shutdown()
            raise

    async def __call__(self, scope, receive, send):
        type = scope["type"]

        _log.debug("Handling event %s", scope)

        if type == "http":
            await self._handle_http_event(scope, receive, send)
        elif type == "lifespan":
            await self._handle_lifespan_event(scope, receive, send)
        else:
            assert False, type # pragma: nocover

    async def _handle_http_event(self, scope, receive, send):
        path = scope["path"]

        for route in self._routes:
            match = route.regex.fullmatch(path)

            if match is not None:
                scope["brbn.path_params"] = match.groupdict()
                await route.resource(self, scope, receive, send)
                return

        await Request(self, scope, receive, send).respond(404, "Not found")

    async def _handle_lifespan_event(self, scope, receive, send):
        while True:
            message = await receive()
            type = message["type"]

            _log.debug("Receiving message %s", message)

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
                assert False, type # pragma: nocover

class _UvicornServer(_uvicorn.Server):
    def __init__(self, config, started, stopped):
        super().__init__(config=config)
        self._brbn_started = started
        self._brbn_stopped = stopped

    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        self._brbn_started.set()

    async def shutdown(self, sockets=None):
        await super().shutdown(sockets=sockets)
        self._brbn_stopped.set()

class _Route:
    def __init__(self, path, resource):
        self.path = path
        self.resource = resource

        regex = _re.sub(r"/\*$", r"(?P<subpath>.*)", path)
        regex = _re.sub(r"{(\w+)}", r"(?P<\1>[^/]+)", regex)

        self.regex = _re.compile(regex)

    def __repr__(self):
        return f"{self.path} -> {self.resource}"

class Resource:
    def __init__(self, app=None, methods=("GET", "HEAD", "POST"), method=None):
        self.app = app
        self.methods = methods

        if method is not None:
            self.methods = (method,)

    def __repr__(self):
        return _format_repr(self)

    async def __call__(self, server, scope, receive, send):
        request = Request(server, scope, receive, send)

        try:
            await self.handle(request)
        except BadRequestError as e:
            await request.respond(400, str(e))
        except Exception as e:
            _log.exception(e)
            trace = _traceback.format_exc()
            print(111, trace) # Need this in debug mode XXX
            await request.respond(500, trace)

    async def handle(self, request):
        if request.method not in self.methods:
            await request.respond(400, "Bad request: Illegal method")
            return

        entity = await self.process(request)
        server_etag = await self.get_etag(request, entity)

        if server_etag is not None:
            server_etag = f'"{server_etag}"'
            client_etag = request.get_header("if-none-match")

            if client_etag == server_etag:
                await request.respond(304)
                return

        if request.method == "HEAD":
            await request.respond(200, etag=server_etag)
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

class Request:
    def __init__(self, server, scope, receive, send):
        self._server = server
        self._scope = scope
        self._receive = receive
        self._send = send
        self._params = scope.get("brbn.path_params", dict())

        query_string = scope["query_string"].decode("utf-8")

        for name, value in _urllib.parse.parse_qsl(query_string):
            self._params[name] = value

    def __repr__(self):
        return _format_repr(self, self.method, self.path)

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

            return message.get("body", "")
        elif type == "http.disconnect": # pragma: nocover
            assert False, type # XXX Need a disconnect exception
        else:
            assert False, type # pragma: nocover

    async def parse_json(self) -> object:
        return _json.loads(await self.get_body())

    async def respond(self, code, content=b"", content_type=None, etag=None):
        assert isinstance(code, int), type(code)
        assert content is None or isinstance(content, (bytes, str)), type(content)
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

        if isinstance(content, str):
            content = content.encode("utf-8")

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

class BadRequestError(Exception):
    pass

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

class StaticDirectoryResource(Resource):
    def __init__(self, dir, app=None):
        super().__init__(app=app, methods=("GET", "HEAD"))

        assert _os.path.isdir(dir), dir

        self.dir = dir

    async def handle(self, request):
        try:
            await super().handle(request)
        except FileNotFoundError:
            await request.respond(404, "Not found")

    async def process(self, request):
        subpath = request.require("subpath")

        assert subpath is not None
        assert subpath.startswith("/"), subpath

        return _os.path.join(self.dir, subpath[1:])

    async def get_etag(self, request, fs_path):
        mtime = _os.path.getmtime(fs_path)
        return _struct.pack("f", mtime).hex()

    async def get_content_type(self, request, fs_path):
        _, ext = _os.path.splitext(fs_path)
        return _content_types_by_extension.get(ext, "text/plain;charset=UTF-8")

    async def render(self, request, fs_path):
        with open(fs_path, "r") as file:
            return file.read()

class PinnedFileResource(Resource):
    def __init__(self, file, app=None):
        super().__init__(app=app, methods=("GET", "HEAD"))

        assert _os.path.isfile(file), file

        with open(file, "r") as f:
            self.content = f.read()

        mtime = _os.path.getmtime(file)
        self.etag = _struct.pack("f", mtime).hex()

        _, ext = _os.path.splitext(file)
        self.content_type = _content_types_by_extension.get(ext, "text/plain;charset=UTF-8")

    async def get_etag(self, request, entity):
        return self.etag

    async def get_content_type(self, request, entity):
        return self.content_type

    async def render(self, request, entity):
        return self.content

class BrbnCommand:
    def __init__(self, server=None):
        self.server = server
        self.parser = _argparse.ArgumentParser(description="Brbn serves HTTP")

        self.parser.add_argument("--host", metavar="HOST", default="localhost",
                                 help="Listen for connections on HOST (default localhost)")
        self.parser.add_argument("--port", metavar="PORT", default=8080, type=int,
                                 help="Listen for connections on PORT (default 8080)")
        self.parser.add_argument("--quiet", action="store_true",
                                 help="Print no logging to the console")
        self.parser.add_argument("--verbose", action="store_true",
                                 help="Print detailed logging to the console")
        self.parser.add_argument("--init-only", action="store_true",
                                 help=_argparse.SUPPRESS)

        if self.server is None:
            self.parser.add_argument("server", metavar="MODULE:SERVER",
                                     help="The module and name of a Brbn Server object")

    def init(self, args=None):
        _logging.basicConfig(level=_logging.ERROR)

        self.args = self.parser.parse_args(args=args)

        if self.args.verbose:
            _logging.getLogger("brbn").setLevel(_logging.DEBUG)
            _logging.getLogger("uvicorn").setLevel(_logging.DEBUG)
        elif not self.args.quiet:
            _logging.getLogger("brbn").setLevel(_logging.INFO)
            _logging.getLogger("uvicorn").setLevel(_logging.INFO)

        if self.server is None:
            module_name, server_name = self.args.server.split(":", 1)
            module = _importlib.import_module(module_name)
            self.server = getattr(module, server_name)

    def main(self, args=None):
        self.init(args=args)

        if self.args.init_only:
            return

        try:
            self.server.run(host=self.args.host, port=self.args.port)
        except KeyboardInterrupt: # pragma: nocover
            pass

def _format_repr(obj, *args):
    cls = obj.__class__.__name__
    strings = [str(x) for x in args]

    return "{}({})".format(cls, ", ".join(strings))

def main(): # pragma: nocover
    BrbnCommand().main()
