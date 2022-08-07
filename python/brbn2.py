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
import starlette.exceptions as _exceptions
import starlette.requests as _requests
import starlette.routing as _routing
import starlette.staticfiles as _staticfiles
import traceback as _traceback
import uvicorn as _uvicorn

from starlette.responses import *

_log = _logging.getLogger("brbn")

class Server:
    def __init__(self, app, host="", port=8080):
        self.app = app
        self.host = host
        self.port = port

        self._startup_coros = list()
        self._router = _Router(self.app, _Lifespan(self))

    def add_route(self, path, endpoint, method=None, methods=["GET", "HEAD"]):
        assert path.startswith("/"), path

        if method is not None:
            methods = [method]

        self._router.add_route(path, endpoint=endpoint, methods=methods)

    def add_static_files(self, path, dir):
        assert path.startswith("/"), path

        self._router.mount(path, app=_staticfiles.StaticFiles(directory=dir, html=True))

    def add_startup_task(self, coro):
        self._startup_coros.append(coro)

    def run(self):
        _uvicorn.run(self._router, host=self.host, port=self.port)

# XXX Maybe we can get rid of this
class _Router(_routing.Router):
    def __init__(self, app, lifespan):
        super().__init__(lifespan=lifespan)

        # self.app = app XXX
        # self.task_coros = list()

    async def __call__(self, scope, receive, send):
        # scope["app"] = self.app XXX

        try:
            await super().__call__(scope, receive, send)
        except _exceptions.HTTPException as e:
            if e.status_code == 404:
                await NotFoundResponse()(scope, receive, send)
            else:
                raise

class _Lifespan():
    def __init__(self, server):
        self.server = server

    def __call__(self, asgi_app):
        return self

    async def __aenter__(self):
        for coro in self.server._startup_coros:
            _asyncio.get_event_loop().create_task(coro)

    async def __aexit__(self, exc_type, exc, exc_tb):
        pass

class Request(_requests.Request):
    pass # XXX

class Endpoint:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        request = Request(scope, receive)

        try:
            response = await self.handle(request)
        except HandlingException as e:
            response = e.response
        except Exception as e:
            response = ServerErrorResponse(e)

        await response(scope, receive, send)

    async def handle(self, request):
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

class HandlingException(Exception):
    def __init__(self, message, response):
        super().__init__(message)
        self.response = response

class Redirect(HandlingException):
    def __init__(self, url):
        super().__init__(url, RedirectResponse(url))

class BadRequestError(HandlingException):
    def __init__(self, message):
        super().__init__(message, BadRequestResponse(message))

class NotFoundError(HandlingException):
    def __init__(self, message):
        super().__init__(message, NotFoundResponse(message))

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

class BadJsonResponse(PlainTextResponse):
    def __init__(self, exception):
        super().__init__(f"Bad request: Failure decoding JSON: {exception}\n", 400)

class OkResponse(Response):
    def __init__(self):
        super().__init__("OK\n")

class HtmlResponse(HTMLResponse):
    pass

class JsonResponse(JSONResponse):
    pass

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
