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
import brbn2 as _brbn
import httpx as _httpx
import logging as _logging
import os as _os
import runpy as _runpy
import sys as _sys
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

        self.model.update_thread.start()

        server.run()

    def main(self):
        _logging.basicConfig(level=_logging.INFO)

        try:
            self.run()
        except KeyboardInterrupt:
            pass

class Server(_brbn.Server):
    def __init__(self, app, host="", port=8080):
        super().__init__(app, host=host, port=port)

        self.add_route("/api/data", endpoint=DataHandler(), methods=["GET", "HEAD"])
        self.add_route("/proxy", endpoint=ProxyHandler(), methods=["GET", "HEAD"])

        self.add_static_files("", _os.path.join(self.app.home, "static"))

class DataHandler(_brbn.Handler):
    async def process(self, request):
        return request.app.model

    def etag(self, request, model):
        return model.update_time

    async def render(self, request, model):
        return _brbn.JsonResponse(model.data())

class ProxyHandler(_brbn.Handler):
    async def process(self, request):
        url = request.query_params["url"]

        async with _httpx.AsyncClient() as client:
            return await client.get(url)

    async def render(self, request, proxied_response):
        return _brbn.Response(proxied_response.text, media_type=proxied_response.headers["content-type"])
