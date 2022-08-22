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
import datetime
import hashlib
import httpx
import inspect
import json
import logging
import os
import runpy
import sys
import time

log = logging.getLogger("blinky.model")

PASSED = "PASSED"
FAILED = "FAILED"

class Model:
    _collections = ["categories", "groups", "agents", "jobs"]

    def __init__(self):
        self.title = "Blinky"
        self.update_time = None
        self.json = None
        self.json_digest = None

        for name in self._collections:
            setattr(self, name, list())

    def __repr__(self):
        return format_repr(self)

    def load(self, config_file):
        if not os.path.exists(config_file):
            config_file = os.path.join("/", "etc", "blinky", "config.py")

        if not os.path.exists(config_file):
            sys.exit("Error! No configuration found")

        log.info("Loading model from {}".format(config_file))

        init_globals = {"model": self}
        config = runpy.run_path(config_file, init_globals)

    def data(self):
        if self.update_time is None:
            raise Exception("The model isn't updated yet")

        data = {
            "title": self.title,
            "update_time": int(round(self.update_time.timestamp() * 1000)),
        }

        for name in self._collections:
            data[name] = dict()

            for item in getattr(self, name):
                data[name][item.id] = item.data()

        return data

    async def update(self):
        log.info("Updating jobs")

        await asyncio.gather(*[x.update() for x in self.agents if x._enabled])

        self.update_time = datetime.datetime.now(datetime.timezone.utc)

        data = self.data()
        prev_json = self.json or ""
        prev_digest = self.json_digest or "-"

        self.json = json.dumps(data, sort_keys=True)
        self.json_digest = hashlib.sha1(self.json.encode("utf-8")).hexdigest()

        log.debug("Prev json: {} {}".format(prev_digest, len(prev_json)))
        log.debug("Curr json: {} {}".format(self.json_digest, len(self.json)))

        log.info("Updated at {}".format(self.update_time))

class ModelObject:
    _references = []
    _reference_collections = []

    def __init__(self, model, collection, name):
        assert isinstance(model, Model), model
        assert isinstance(collection, list), collection
        assert isinstance(name, (str, type(None))), name

        self._model = model
        self.id = len(collection)
        self.name = name

        collection.append(self)

    def __repr__(self):
        return format_repr(self, self.id, self.name)

    def data(self, exclude=()):
        data = dict()

        for key, value in inspect.getmembers(self):
            if key.startswith("_") or inspect.isroutine(value) or key in exclude:
                continue

            if key in self._references:
                data[f"{key}_id"] = value.id if value is not None else None
            elif key in self._reference_collections:
                data["{}_ids".format(key.removesuffix("s"))] = [x.id for x in getattr(self, key)]
            else:
                data[key] = value

        return data

class Category(ModelObject):
    _reference_collections = ["groups"]

    def __init__(self, model, name, key):
        super().__init__(model, model.categories, name)

        assert isinstance(key, str), key

        self.key = key
        self.groups = list()

class Group(ModelObject):
    _references = ["category"]
    _reference_collections = ["jobs"]

    def __init__(self, category, name, fields=["agent", "name", "variant"]):
        super().__init__(category._model, category._model.groups, name)

        assert isinstance(category, Category), category

        self.category = category
        self.fields = fields
        self.jobs = list()

        self.category.groups.append(self)

class Agent(ModelObject):
    _reference_collections = ["jobs"]

    def __init__(self, model, name, enabled=True, token=None):
        super().__init__(model, model.agents, name)

        self.html_url = None
        self.data_url = None
        self.jobs = list()

        self._enabled = enabled
        self._token = token

    async def update(self):
        raise NotImplementedError()

class Job(ModelObject):
    _references = ["group", "agent"]

    def __init__(self, agent, group, name=None, variant=None):
        super().__init__(group._model, group._model.jobs, name)

        assert isinstance(agent, Agent), agent
        assert isinstance(group, Group), group

        self.agent = agent
        self.group = group
        self.variant = variant

        self.agent.jobs.append(self)
        self.group.jobs.append(self)

        self.current_run = None
        self.previous_run = None
        self.update_failures = 0

        self.html_url = None
        self.data_url = None
        self.fetch_url = None

    def data(self):
        data = super().data(exclude=("current_run", "previous_run"))

        if self.current_run is not None:
            data["current_run"] = self.current_run.data()

        if self.previous_run is not None:
            data["previous_run"] = self.previous_run.data()

        return data

    async def update(self, context):
        data = await self.fetch_data(context)

        if data is None:
            self.update_failures += 1
            return

        try:
            run = self.convert_run(data)
        except KeyboardInterrupt:
            raise
        except:
            self.update_failures += 1

            log.exception("Failure converting {}".format(self))

            return

        assert run is not None

        self.update_failures = 0

        if self.current_run and self.current_run.number == run.number:
            self.current_run = run
        else:
            if self.current_run is not None:
                self.previous_run = self.current_run

            self.current_run = run

    async def fetch_data(self, context):
        raise NotImplementedError()

    def convert_run(self, data):
        raise NotImplementedError()

class JobRun:
    def __init__(self):
        self.number = None      # Run sequence number
        self.status = None      # Status string (PASSED, FAILED, [other])
        self.start_time = None  # Start time in milliseconds
        self.duration = None    # Duration in milliseconds
        self.html_url = None    # World Wide Web URL
        self.data_url = None    # Usually a JSON URL
        self.tests_url = None   # Test results
        self.logs_url = None    # Log output

    def data(self):
        return {k: v for k, v in inspect.getmembers(self) if not k.startswith("_") and not inspect.isroutine(v)}

class HttpAgent(Agent):
    async def update(self, headers={}):
        start = time.time()

        if self._token:
            headers["Authorization"] = f"token {self._token}"

        async with httpx.AsyncClient(headers=headers, verify=False) as client:
            start = time.time()

            await asyncio.gather(*[x.update(client) for x in self.jobs])

            elapsed = time.time() - start
            count = len(self.jobs)
            noun = plural('job', count)

            log.info(f"{self} updated {count} {noun} in {elapsed:.2f}s")

class HttpJob(Job):
    async def fetch_data(self, client):
        url = self.data_url

        if self.fetch_url is not None:
            url = self.fetch_url

        log.debug("Fetching data from {}".format(url))

        try:
            response = await client.get(url)
        except httpx.RequestError as e:
            self.log_request_error(e, url, None)
        except Exception as e:
            log.warn("{}: {}: {}".format(e.__class__.__name__, e, url))
        else:
            if response.status_code != 200:
                self.log_request_error(response.status_code, url, response)
                return

            return response.json()

    def log_request_error(self, message, url, response):
        log.warn("Request error:    {}".format(message))
        log.warn("Request URL:      {}".format(url))

        if response is not None:
            log.warn("Response headers: {}".format(response.headers))

            if response.status_code == 500:
                log.warn("Response text:    {}".format(response.text))
            else:
                log.debug("Response text:    {}".format(response.text))

def parse_timestamp(timestamp, format="%Y-%m-%dT%H:%M:%SZ"):
    if timestamp is None:
        return None

    dt = datetime.datetime.strptime(timestamp, format)
    dt = dt.replace(tzinfo=datetime.timezone.utc)

    return int(round(dt.timestamp() * 1000))

def format_repr(obj, *args):
    cls = obj.__class__.__name__
    strings = [str(x) for x in args]

    return "{}({})".format(cls, ", ".join(strings))

def plural(noun, count=0, plural=None):
    if count == 1:
        return noun

    if plural is None:
        if noun.endswith("s"):
            plural = "{}ses".format(noun)
        else:
            plural = "{}s".format(noun)

    return plural
