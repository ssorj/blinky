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

from brbn import *
from brbn.plano import *

static_dir = make_temp_dir()

write(join(static_dir, "alpha.txt"), "alpha")
write(join(static_dir, "beta.html"), "beta")

server = Server()

class Main(Resource):
    async def render(self, request, entity):
        return "main"

class Explode(Resource):
    async def process(self, request):
        raise Exception()

class Json(Resource):
    async def process(self, request):
        data = await request.parse_json()

class RequiredParam(Resource):
    async def process(self, request):
        not_there = request.require("not-there")

server.add_route("/", Main())
server.add_route("/explode", Explode())
server.add_route("/files/alpha.txt", PinnedFileResource(join(static_dir, "alpha.txt")))
server.add_route("/files/*", StaticDirectoryResource(static_dir))
server.add_route("/json", Json())
server.add_route("/post-only", Resource(method="POST"))
server.add_route("/required-param", RequiredParam())
