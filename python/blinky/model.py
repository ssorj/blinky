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

import collections as _collections
import concurrent.futures as _futures
import datetime as _datetime
import hashlib as _hashlib
import inspect as _inspect
import json as _json
import logging as _logging
import os as _os
import requests as _requests
import runpy as _runpy
import sched as _sched
import threading as _threading
import time as _time

_log = _logging.getLogger("blinky.model")

PASSED = "PASSED"
FAILED = "FAILED"

class Model:
    def __init__(self):
        self.title = "Blinky"

        self.update_thread = ModelUpdateThread(self)
        self.update_time = None

        self.executor = _futures.ThreadPoolExecutor()

        self.categories = list()
        self.groups = list()
        self.components = list()
        self.environments = list()
        self.agents = list()
        self.jobs = list()

        self.json = None
        self.json_digest = None

    def __repr__(self):
        return format_repr(self)

    def load(self, config_file):
        if not _os.path.exists(config_file):
            config_file = _os.path.join("/", "etc", "blinky", "config.py")

        if not _os.path.exists(config_file):
            _sys.exit("Error! No configuration found")

        _log.info("Loading model from {}".format(config_file))

        init_globals = {"model": self}
        config = _runpy.run_path(config_file, init_globals)

    def data(self):
        if self.update_time is None:
            raise Exception("The model isn't updated yet")

        data = {
            "title": self.title,
            "update_time": int(round(self.update_time.timestamp() * 1000)),
        }

        categories_data = data["categories"] = dict()
        groups_data = data["groups"] = dict()
        components_data = data["components"] = dict()
        environments_data = data["environments"] = dict()
        agents_data = data["agents"] = dict()
        jobs_data = data["jobs"] = dict()

        for category in self.categories:
            categories_data[category.id] = category.data()

        for group in self.groups:
            groups_data[group.id] = group.data()

        for component in self.components:
            components_data[component.id] = component.data()

        for environment in self.environments:
            environments_data[environment.id] = environment.data()

        for agent in self.agents:
            agents_data[agent.id] = agent.data()

        for job in self.jobs:
            jobs_data[job.id] = job.data()

        return data

    def update(self):
        _log.info("Updating jobs".format(self))

        futures = [self.executor.submit(x.update) for x in self.agents if x.enabled]

        for future in _futures.as_completed(futures):
            if future.exception() is not None:
                _log.error("Failure updating: {}".format(future.exception()))

        self.update_time = _datetime.datetime.now(_datetime.timezone.utc)

        data = self.data()

        prev_json = self.json or ""
        prev_digest = self.json_digest or "-"

        self.json = _json.dumps(data, sort_keys=True).encode("utf-8")
        self.json_digest = _hashlib.sha1(self.json).hexdigest()

        _log.debug("Prev json: {} {}".format(prev_digest, len(prev_json)))
        _log.debug("Curr json: {} {}".format(self.json_digest, len(self.json)))

        _log.info("Updated at {}".format(self.update_time))

class ModelUpdateThread(_threading.Thread):
    def __init__(self, model):
        super().__init__()

        self.model = model
        self.name = "ModelUpdateThread"
        self.daemon = True

        self.scheduler = _sched.scheduler()

    def start(self):
        _log.info("Starting update thread")

        super().start()

    def run(self):
        self.update_model()
        self.scheduler.run()

    def update_model(self):
        self.scheduler.enter(20 * 60, 1, self.update_model)

        try:
            self.model.update()
        except KeyboardInterrupt:
            raise
        except:
            _log.exception("Update failed")

class ModelObject:
    _single_reference_keys = []
    _multiple_reference_keys = []

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

    def data(self):
        # XXX Use a loop!

        data = {k: v for k, v in _inspect.getmembers(self)
                if not k.startswith("_")
                and not _inspect.isroutine(v)
                and k not in self._single_reference_keys
                and k not in self._multiple_reference_keys}

        for key in self._single_reference_keys:
            value = getattr(self, key)

            if value is not None:
                value = value.id

            data[f"{key}_id"] = value

        for key in self._multiple_reference_keys:
            data["{}_ids".format(key.removesuffix("s"))] = [x.id for x in getattr(self, key)]

        return data

class Category(ModelObject):
    _multiple_reference_keys = ["groups"]

    def __init__(self, model, name, key):
        super().__init__(model, model.categories, name)

        assert isinstance(key, str), key

        self.key = key
        self.groups = list()

class Group(ModelObject):
    _single_reference_keys = ["category"]
    _multiple_reference_keys = ["jobs"]

    def __init__(self, category, name, fields=["agent", "name"]):
        super().__init__(category._model, category._model.groups, name)

        assert isinstance(category, Category), category

        self.category = category
        self.fields = fields
        self.jobs = list()

        self.category.groups.append(self)

class Component(ModelObject):
    _multiple_reference_keys = ["jobs"]

    def __init__(self, model, name):
        super().__init__(model, model.components, name)

        self.jobs = list()

class Environment(ModelObject):
    _multiple_reference_keys = ["jobs"]

    def __init__(self, model, name):
        super().__init__(model, model.environments, name)

        self.jobs = list()

class Agent(ModelObject):
    _multiple_reference_keys = ["jobs"]

    def __init__(self, model, name):
        super().__init__(model, model.agents, name)

        self.html_url = None
        self.data_url = None
        self.token = None
        self.enabled = True
        self.jobs = list()

    def update(self):
        raise NotImplementedError()

class Job(ModelObject):
    _single_reference_keys = ["group", "agent", "component", "environment"]

    def __init__(self, group, component, environment, agent, name):
        super().__init__(group._model, group._model.jobs, name)

        assert isinstance(group, Group), group
        assert isinstance(agent, Agent), agent

        if component is not None:
            assert isinstance(component, Component), component

        if environment is not None:
            assert isinstance(environment, Environment), environment

        self.group = group
        self.agent = agent
        self.branch = None
        self.component = component
        self.environment = environment

        self.group.jobs.append(self)
        self.agent.jobs.append(self)

        # XXX RHS if?
        if component is not None:
            self.component.jobs.append(self)

        if environment is not None:
            self.environment.jobs.append(self)

        self.current_run = None
        self.previous_run = None
        self.update_failures = 0

        self.html_url = None
        self.data_url = None
        self.fetch_url = None

    def update(self, context):
        data = self.fetch_data(context)

        if data is None:
            self.update_failures += 1
            return

        try:
            run = self.convert_run(data)
        except KeyboardInterrupt:
            raise
        except:
            self.update_failures += 1

            _log.exception("Failure converting {}".format(self))

            return

        assert run is not None

        self.update_failures = 0

        if self.current_run and self.current_run.number == run.number:
            self.current_run = run
        else:
            if self.current_run is not None:
                self.previous_run = self.current_run.data()

            self.current_run = run.data()

    def fetch_data(self, context):
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
        return {k: v for k, v in _inspect.getmembers(self) if not k.startswith("__") and not _inspect.isroutine(v)}

class HttpAgent(Agent):
    def update(self):
        start = _time.time()

        with _requests.Session() as session:
            for job in self.jobs:
                job.update(session)

        elapsed = _time.time() - start

        _log.info("{} updated {} jobs in {:.2f}s".format(self, len(self.jobs), elapsed))

class HttpJob(Job):
    def fetch_data(self, session, headers={}):
        if self.agent.token:
            headers["Authorization"] = f"token {self.agent.token}"

        url = self.data_url

        if self.fetch_url is not None:
            url = self.fetch_url

        try:
            _log.debug("Fetching data from {}".format(url))

            response = session.get(url, headers=headers, timeout=5)
        except _requests.exceptions.ConnectionError:
            raise
        except _requests.exceptions.RequestException as e:
            self.log_request_error(str(e), url, headers, None)
            return

        if response.status_code != 200:
            message = str(response.status_code)
            self.log_request_error(message, url, headers, response)
            return

        return response.json()

    def log_request_error(self, message, url, headers, response):
        _log.warn("HTTP request error: {}".format(message))
        _log.warn("Request URL:        {}".format(url))

        if headers is not None:
            _log.warn("Request headers:    {}".format(headers))

        if response is not None:
            _log.warn("Response code:      {}".format(response.status_code))
            _log.warn("Response headers:   {}".format(response.headers))

            if response.status_code == 500:
                _log.warn("Response text:      {}".format(response.text))
            else:
                _log.debug("Response text:      {}".format(response.text))

def parse_timestamp(timestamp, format="%Y-%m-%dT%H:%M:%SZ"):
    if timestamp is None:
        return None

    dt = _datetime.datetime.strptime(timestamp, format)
    dt = dt.replace(tzinfo=_datetime.timezone.utc)

    return int(round(dt.timestamp() * 1000))

def format_repr(obj, *args):
    cls = obj.__class__.__name__
    strings = [str(x) for x in args]
    return "{}({})".format(cls, ",".join(strings))
