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

import asyncio
import brbn
import httpx
import logging
import os
import time

from .model import Model

_log = logging.getLogger("blinky.main")

_description = "Blinky collects and displays results from CI jobs"

_epilog = """
Blinky looks for its configuration in the following locations:

  1. The FILE indicated by --config
  2. $HOME/.config/blinky/config.py
  3. /etc/blinky/config.py
"""

class BlinkyCommand(brbn.BrbnCommand):
    def __init__(self, home):
        super().__init__(server=brbn.Server())

        self.home = home
        self.static_dir = os.path.join(self.home, "static")

        self.parser.description = _description
        self.parser.epilog = _epilog

        user_dir = os.path.expanduser("~")
        default_config_file = os.path.join(user_dir, ".config", "blinky", "config.py")

        self.parser.add_argument("--config", default=default_config_file, metavar="FILE",
                                 help="Load configuration from FILE")

    def init(self, args=None):
        super().init(args=args)

        self.model = Model()
        self.model.load(self.args.config)

        main = brbn.PinnedFileResource(os.path.join(self.static_dir, "main.html"))
        data = DataResource(app=self)
        proxy = ProxyResource(app=self)
        files = brbn.StaticDirectoryResource(self.static_dir)

        self.server.add_route("/", main)
        self.server.add_route("/api/data", data)
        self.server.add_route("/pretty", main)
        self.server.add_route("/proxy", proxy)
        self.server.add_route("/*", files)

        self.server.add_startup_task(self.update())

        self.server.csp = "default-src 'self' *.googleapis.com *.gstatic.com"

    async def update(self):
        while True:
            start = time.time()
            await self.model.update()
            elapsed = time.time() - start

            await asyncio.sleep(max(0, 30 * 60 - elapsed))

class DataResource(brbn.Resource):
    async def process(self, request):
        return self.app.model

    async def get_etag(self, request, model):
        return model.json_digest

    async def get_content_type(self, request, model):
        return "text/json"

    async def render(self, request, model):
        return model.json

class ProxyResource(brbn.Resource):
    async def process(self, request):
        url = request.require("url")

        async with httpx.AsyncClient() as client:
            return await client.get(url)

    async def get_content_type(self, request, proxied_response):
        return proxied_response.headers["content-type"]

    async def render(self, request, proxied_response):
        return proxied_response.text
