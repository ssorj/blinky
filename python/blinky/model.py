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
import json as _json
import hashlib as _hashlib
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
    def __init__(self, model, collection, name):
        assert isinstance(model, Model), model
        assert isinstance(collection, list), collection
        assert isinstance(name, (str, type(None))), name

        self.model = model
        self.id = len(collection)
        self.name = name

        collection.append(self)

    def __repr__(self):
        return format_repr(self, self.id, self.name)

    def data(self):
        data = dict()
        data["id"] = self.id
        data["name"] = self.name

        if hasattr(self, "jobs"):
            data["job_ids"] = [x.id for x in self.jobs]

        return data

class Category(ModelObject):
    def __init__(self, model, name, key):
        super().__init__(model, model.categories, name)

        assert isinstance(key, str), key

        self.key = key

        self.groups = list()

    def data(self):
        data = super().data()
        data["key"] = self.key
        data["group_ids"] = [x.id for x in self.groups]

        return data

class Group(ModelObject):
    def __init__(self, model, category, name):
        super().__init__(model, model.groups, name)

        assert isinstance(category, Category), category

        self.category = category

        self.jobs = list()

        self.category.groups.append(self)

    def data(self):
        data = super().data()
        data["category_id"] = self.category.id

        return data

class Component(ModelObject):
    def __init__(self, model, name):
        super().__init__(model, model.components, name)

        self.jobs = list()

class Environment(ModelObject):
    def __init__(self, model, name):
        super().__init__(model, model.environments, name)

        self.jobs = list()

class Agent(ModelObject):
    def __init__(self, model, name):
        super().__init__(model, model.agents, name)

        self.html_url = None
        self.data_url = None
        self.token = None
        self.enabled = True

        self.jobs = list()

    def update(self):
        raise NotImplementedError()

    def data(self):
        data = super().data()
        data["html_url"] = self.html_url
        data["data_url"] = self.data_url

        return data

class Job(ModelObject):
    def __init__(self, model, group, component, environment, agent, name):
        super().__init__(model, model.jobs, name)

        assert isinstance(group, Group), group
        assert isinstance(component, Component), component
        assert isinstance(environment, Environment), environment
        assert isinstance(agent, Agent), agent

        self.group = group
        self.component = component
        self.environment = environment
        self.agent = agent

        self.group.jobs.append(self)
        self.component.jobs.append(self)
        self.environment.jobs.append(self)
        self.agent.jobs.append(self)

        self.results = _collections.deque(maxlen=2)
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
            result = self.convert_result(data)
        except KeyboardInterrupt:
            raise
        except:
            self.update_failures += 1

            _log.exception("Failure converting {}".format(self))

            return

        assert result is not None

        self.update_failures = 0

        if self.current_result and self.current_result.number == result.number:
            self.results[-1] = result
        else:
            self.results.append(result)

    def fetch_data(self, context):
        raise NotImplementedError()

    def convert_result(self, data):
        raise NotImplementedError()

    @property
    def current_result(self):
        if len(self.results) >= 1:
            return self.results[-1]

    @property
    def previous_result(self):
        if len(self.results) >= 2:
            return self.results[-2]

    def data(self):
        data = super().data()

        data["group_id"] = self.group.id
        data["component_id"] = self.component.id
        data["environment_id"] = self.environment.id
        data["agent_id"] = self.agent.id
        data["html_url"] = self.html_url
        data["data_url"] = self.data_url

        data["previous_result"] = None
        data["current_result"] = None

        if self.previous_result:
            data["previous_result"] = self.previous_result.data()

        if self.current_result:
            data["current_result"] = self.current_result.data()

        data["update_failures"] = self.update_failures

        return data

class JobResult:
    def __init__(self):
        self.number = None      # Result sequence number
        self.status = None      # Status string (PASSED, FAILED, [other])
        self.start_time = None  # Start time in milliseconds
        self.duration = None    # Duration in milliseconds
        self.html_url = None    # World Wide Web URL
        self.data_url = None    # Usually a JSON URL
        self.tests_url = None   # Test results
        self.logs_url = None    # Log output

    def data(self):
        data = dict()

        data["number"] = self.number
        data["status"] = self.status
        data["start_time"] = self.start_time
        data["duration"] = self.duration
        data["html_url"] = self.html_url
        data["data_url"] = self.data_url
        data["tests_url"] = self.tests_url
        data["logs_url"] = self.logs_url

        return data

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
