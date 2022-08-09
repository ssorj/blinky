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
import logging as _logging
import os as _os
import re as _re
import starlette.requests as _requests
import starlette.responses as _responses
import starlette.staticfiles as _staticfiles
import traceback as _traceback
import uvicorn as _uvicorn

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

    def add_route(self, path, endpoint):
        _log.info(f"Adding route: {path} -> {endpoint}")

        assert path.startswith("/"), path
        assert path == "/" or not path.endswith("/"), path

        self._routes.append(_Route(path, endpoint))

    def add_static_files(self, path, dir):
        assert path.startswith("/"), path

        # self._router.mount(path, app=_staticfiles.StaticFiles(directory=dir, html=True))

    def run(self):
        _uvicorn.run(self, host=self.host, port=self.port, lifespan="on")

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
            if route.regex.fullmatch(path) is not None:
                try:
                    await route.endpoint(scope, receive, send)
                except _EndpointException as e:
                    await e.response(scope, receive, send)
                except Exception as e:
                    await ServerErrorResponse(e)(scope, receive, send)

                return

        # XXX

        file_path = _os.path.join("/home/jross/code/blinky/static", path[1:])

        print(111, file_path)

        if _os.path.exists(file_path):
            print(222)
            await FileResponse(file_path)(scope, receive, send)
            return

        # End XXX

        await NotFoundResponse()(scope, receive, send)

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
    def __init__(self, path, endpoint):
        self.path = path
        self.endpoint = endpoint
        self.regex = _re.sub(r"{(\w+)}", r"(?P<\1>[^/]+)", path) + r"/*"
        self.regex = _re.compile(self.regex)

class Request:
    def __init__(self, scope, receive):
        self._request = _requests.Request(scope, receive)

    def get(self, param, default=None):
        try:
            return self._request.query_params[param]
        except KeyError:
            try:
                return self._request.path_params[param]
            except KeyError:
                return default

    def require(self, param):
        value = self.get(param)

        if value is None:
            raise BadRequestError(f"Required parameter not found: {param}")

        return value

    @property
    def method(self):
        return self._request.method

    @property
    def headers(self):
        return self._request.headers

    def json(self):
        return self._request.json()

class Endpoint:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        request = Request(scope, receive)
        response = await self.respond(request)

        await response(scope, receive, send)

    async def respond(self, request):
        entity = await self.process(request)
        server_etag = self.etag(request, entity)

        if server_etag is not None:
            server_etag = f'"{server_etag}"'
            client_etag = request.headers.get("if-none-match")

            if client_etag == server_etag:
                return NotModifiedResponse()

        if request.method == "HEAD":
            response = Response("")
        else:
            response = await self.render(request, entity)
            assert response is not None

        if server_etag is not None:
            response.headers["etag"] = server_etag

        return response

    async def process(self, request):
        return None

    def etag(self, request, entity):
        pass

    async def render(self, request, entity):
        return OkResponse()

class _EndpointException(Exception):
    def __init__(self, message, response):
        super().__init__(message)
        self.response = response

class Redirect(_EndpointException):
    def __init__(self, url):
        super().__init__(url, RedirectResponse(url))

class BadRequestError(_EndpointException):
    def __init__(self, message):
        super().__init__(message, BadRequestResponse(message))

class NotFoundError(_EndpointException):
    def __init__(self, message):
        super().__init__(message, NotFoundResponse(message))

class Response(_responses.Response):
    pass

class PlainTextResponse(_responses.PlainTextResponse):
    pass

class HtmlResponse(_responses.HTMLResponse):
    pass

class FileResponse(_responses.FileResponse):
    pass

class OkResponse(Response):
    def __init__(self):
        super().__init__("OK\n")

class BadRequestResponse(PlainTextResponse):
    def __init__(self, exception):
        super().__init__(f"Bad request: {exception}\n", 400)

class NotFoundResponse(PlainTextResponse):
    def __init__(self):
        super().__init__(f"Not found\n", 404)

class NotModifiedResponse(Response):
    def __init__(self):
        super().__init__("", 304)

class ServerErrorResponse(PlainTextResponse):
    def __init__(self, exception):
        super().__init__(f"Internal server error: {exception}\n", 500)
        _traceback.print_exc()

class JsonResponse(_responses.JSONResponse):
    pass

class BadJsonResponse(PlainTextResponse):
    def __init__(self, exception):
        super().__init__(f"Bad request: Failure decoding JSON: {exception}\n", 400)

class CompressedJsonResponse(Response):
    def __init__(self, content):
        super().__init__(content, headers={"Content-Encoding": "gzip"}, media_type="application/json")

_directory_index_template = """
<html>
  <head>
    <title>{title}</title>
    <link rel="icon" href="data:,">
  </head>
  <body><pre>{lines}</pre></body>
</html>
""".strip()

class DirectoryIndexResponse(HtmlResponse):
    def __init__(self, base_dir, file_path):
        super().__init__(self.make_index(base_dir, file_path))

    def make_index(self, base_dir, request_path):
        assert not request_path.startswith("/")

        if request_path != "/" and request_path.endswith("/"):
            request_path = request_path[:-1]

        fs_path = _os.path.join(base_dir, request_path)

        assert _os.path.isdir(fs_path), fs_path

        names = _os.listdir(fs_path)
        lines = list()

        if request_path == "":
            lines.append("..")

            for name in names:
                lines.append(f"<a href=\"/{name}\">{name}</a>")
        else:
            lines.append(f"<a href=\"/{request_path}/..\">..</a>")

            for name in names:
                lines.append(f"<a href=\"/{request_path}/{name}\">{name}</a>")

        html = _directory_index_template.format(title=request_path, lines="\n".join(lines))

        return html
