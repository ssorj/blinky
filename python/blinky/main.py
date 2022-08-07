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
import brbn2 as _brbn
import httpx as _httpx
import logging as _logging
import os as _os
import runpy as _runpy
import sys as _sys
import time as _time
import uuid as _uuid

from .model import Model

_log = _logging.getLogger("blinky.main")

_description = "Blinky collects and displays results from CI jobs"

_epilog = """
Blinky looks for its configuration in the following locations:

  1. The FILE indicated by --config
  2. $HOME/.config/blinky/config.py
  3. /etc/blinky/config.py
"""

class BlinkyCommand:
    def __init__(self, home):
        self.home = home
        self.model = Model()

        self.parser = _argparse.ArgumentParser(description=_description, epilog=_epilog,
                                               formatter_class=_argparse.RawDescriptionHelpFormatter)

        user_dir = _os.path.expanduser("~")
        default_config_file = _os.path.join(user_dir, ".config", "blinky", "config.py")

        self.parser.add_argument("--config", default=default_config_file, metavar="FILE",
                                 help="Load configuration from FILE")

        self.parser.add_argument("--init-only", action="store_true",
                                 help="Initialize then exit")

    def run(self):
        args = self.parser.parse_args()

        self.model.load(args.config)

        server = Server(self, port=8080)

        if args.init_only:
            return

        server.run()

    def main(self):
        _logging.basicConfig(level=_logging.ERROR)
        _logging.getLogger("blinky").setLevel(_logging.INFO)

        try:
            self.run()
        except KeyboardInterrupt:
            pass

class ModelUpdateTask():
    def __init__(self, app):
        self.app = app

    async def __aenter__(self):
        _asyncio.get_event_loop().create_task(self.update())

    async def __aexit__(self, exc_type, exc, exc_tb):
        pass

    async def update(self):
        while True:
            start = _time.time()
            await self.app.model.update()
            elapsed = _time.time() - start

            await _asyncio.sleep(max(0, 30 * 60 - elapsed))

class Server(_brbn.Server):
    def __init__(self, app, host="", port=8080):
        super().__init__(app, host=host, port=port, lifespan=ModelUpdateTask)

        main = MainEndpoint() # Makes sense to take app here XXX
        data = DataEndpoint()
        proxy = ProxyEndpoint()

        self.add_route("/", main)
        self.add_route("/pretty", main)
        self.add_route("/api/data", data)
        self.add_route("/proxy", proxy)

        self.add_static_files("/", _os.path.join(self.app.home, "static"))

class MainEndpoint(_brbn.Endpoint):
    async def render(self, request, entity):
        with open(_os.path.join(request.app.home, "static", "main.html")) as file:
            html = file.read()

        return _brbn.HtmlResponse(html)

class DataEndpoint(_brbn.Endpoint):
    async def process(self, request):
        return request.app.model

    def etag(self, request, model):
        return model.update_time

    async def render(self, request, model):
        return _brbn.JsonResponse(model.data())

class ProxyEndpoint(_brbn.Endpoint):
    async def process(self, request):
        url = request.query_params["url"]

        async with _httpx.AsyncClient() as client:
            return await client.get(url)

    async def render(self, request, proxied_response):
        return _brbn.Response(proxied_response.text, media_type=proxied_response.headers["content-type"])
