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

from .main import *
from .plano import *
from . import testapp

import asyncio
import httpx

class TestServer:
    def __init__(self, server=testapp.server):
        self.server = server

    async def __aenter__(self):
        port = get_random_port()

        await self.server.start(host="localhost", port=port)

        return f"http://localhost:{port}"

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.server.stop()

@test
async def server():
    server = Server()

    result = server.__repr__()
    assert result.startswith("Server"), result

    await server.stop()
    await server.start(host="localhost", port=get_random_port())

    with expect_exception():
        await server.start(host="localhost", port=get_random_port())

    await server.stop()
    await server.stop()

    async def hello():
        print("Hello")

    async def goodbye():
        print("Goodbye")

    server = Server()
    server.add_startup_task(hello())
    server.add_shutdown_task(goodbye())

    async with TestServer(server):
        pass

@test
def request():
    server = Server()
    scope = {
        "method": "GET",
        "path": "/",
        "query_string": "bob=1&alice=2".encode("utf-8"),
    }

    request = Request(server, scope, None, None)

    result = request.__repr__()
    assert result.startswith("Request"), result

    result = request.get("bob")
    assert result == "1", result

    result = request.get("frank", "10")
    assert result == "10", result

    result = request.require("alice")
    assert result == "2", result

    with expect_exception(BadRequestError):
        request.require("not-there")

@test
async def command():
    # Missing MODULE:SERVER
    with expect_system_exit():
        BrbnCommand().main(["--init-only"])

    with expect_exception(ModuleNotFoundError):
        BrbnCommand().main(["--init-only", "somemodule:someserver"])

    command = BrbnCommand()
    command.main(["--init-only", "brbn.testapp:server"])

    command = BrbnCommand()
    command.main(["--verbose", "--init-only", "brbn.testapp:server"])

    command = BrbnCommand()
    command.main(["--quiet", "--init-only", "brbn.testapp:server"])

    from threading import Thread

    class TestThread(Thread):
        def __init__(self):
            super().__init__()
            self.command = BrbnCommand(server=testapp.server)

        def start(self):
            super().start()

            while self.command.server._loop is None:
                sleep(0.1)

        def run(self):
            self.command.main(args=["--port", str(get_random_port())])

        def stop(self):
            asyncio.run_coroutine_threadsafe(self.command.server.stop(), self.command.server._loop)

    thread = TestThread()
    thread.start()
    thread.stop()
    thread.join()

# XXX Achieve better coverage without running the client_server tests
# @test(disabled=True)
@test
async def client_server():
    async with TestServer() as url:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            assert response.status_code == 200, response.status_code
            assert response.text == "main", response.text

            response = await client.head(url)
            assert response.status_code == 200, response.status_code

            response = await client.get(f"{url}/explode")
            assert response.status_code == 500, response.status_code

            response = await client.get(f"{url}/not-there")
            assert response.status_code == 404, response.status_code

            response = await client.get(f"{url}/files/alpha.txt")
            assert response.status_code == 200, response.status_code
            assert response.headers["content-type"].startswith("text/plain"), response.headers["content-type"]
            assert response.text == "alpha", response.text

            response = await client.get(f"{url}/files/alpha.txt", headers={"if-none-match": response.headers["etag"]})
            assert response.status_code == 304, response.status_code

            response = await client.get(f"{url}/files/beta.html")
            assert response.status_code == 200, response.status_code
            assert response.headers["content-type"].startswith("text/html"), response.headers["content-type"]
            assert "beta" in response.text, response.text

            response = await client.get(f"{url}/files/not-there")
            assert response.status_code == 404, response.status_code

            response = await client.post(f"{url}/json", json={"a": [1, 2, 3]})
            assert response.status_code == 200, response.status_code

            response = await client.get(f"{url}/post-only")
            assert response.status_code == 400, response.status_code

            response = await client.get(f"{url}/required-param")
            assert response.status_code == 400, response.status_code

def main():
    from . import tests

    PlanoTestCommand(tests).main()
