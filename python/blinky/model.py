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
import datetime as _datetime
import json as _json
import hashlib as _hashlib
import logging as _logging
import pencil as _pencil
import pprint as _pprint
import requests as _requests
import threading as _threading
import time as _time

_log = _logging.getLogger("blinky.model")

class Model:
    def __init__(self):
        self.update_thread = _ModelUpdateThread(self)
        self.update_time = None
        
        self.groups = list()
        self.components = list()
        self.environments = list()
        self.agents = list()
        self.jobs = list()

        self.json = None
        self.json_digest = None

    def __repr__(self):
        return _pencil.format_repr(self)

    def render_data(self):
        data = dict()

        if self.update_time is None:
            raise Exception("The model isn't updated yet")

        time = self.update_time.timetuple()
        time = _time.mktime(time) + 1e-6 * self.update_time.microsecond

        data["update_timestamp"] = time
        
        groups_data = data["groups"] = dict()
        components_data = data["components"] = dict()
        environments_data = data["environments"] = dict()
        agents_data = data["agents"] = dict()
        jobs_data = data["jobs"] = dict()
        
        for group in self.groups:
            groups_data[group.id] = group.render_data()

        for component in self.components:
            components_data[component.id] = component.render_data()

        for environment in self.environments:
            environments_data[environment.id] = environment.render_data()

        for agent in self.agents:
            agents_data[agent.id] = agent.render_data()

        for job in self.jobs:
            jobs_data[job.id] = job.render_data()

        return data
        
    def update(self):
        _log.info("Updating {}".format(self))
        
        for agent in self.agents:
            try:
                agent.update()
            except:
                _log.exception("Failure updating {}".format(agent))

        self.update_time = _datetime.datetime.utcnow()

        data = self.render_data()

        prev_json = self.json or ""
        prev_digest = self.json_digest or "-"
        
        self.json = _json.dumps(data, sort_keys=True).encode("utf-8")
        self.json_digest = _hashlib.sha1(self.json).hexdigest()

        _log.info("Prev json: {} {}".format(prev_digest, len(prev_json)))
        _log.info("Curr json: {} {}".format(self.json_digest, len(self.json)))
        
        _log.info("Updated at {}".format(self.update_time))

class _ModelUpdateThread(_threading.Thread):
    def __init__(self, model):
        super().__init__()

        self.model = model
        self.name = "_ModelUpdateThread"
        self.daemon = True

    def start(self):
        _log.info("Starting update thread")
        
        super().start()

    def run(self):
        while True:
            _time.sleep(120)

            try:
                self.model.update()
            except:
                _log.exception("Unexpected error")

class _ModelObject:
    def __init__(self, model, collection, name):
        assert isinstance(model, Model), model
        assert isinstance(collection, list), collection
        assert isinstance(name, str), name
        
        self.model = model
        self.id = len(collection)
        self.name = name

        collection.append(self)

    def __repr__(self):
        return _pencil.format_repr(self, self.id, self.name)

    def render_data(self):
        data = dict()
        data["id"] = self.id
        data["name"] = self.name
            
        if hasattr(self, "jobs"):
            data["job_ids"] = [x.id for x in self.jobs]
        
        return data
        
class Group(_ModelObject):
    def __init__(self, model, name):
        super().__init__(model, model.groups, name)
        self.jobs = list()
        
class Component(_ModelObject):
    def __init__(self, model, name):
        super().__init__(model, model.components, name)
        self.jobs = list()

class Environment(_ModelObject):
    def __init__(self, model, name):
        super().__init__(model, model.environments, name)
        self.jobs = list()

class Agent(_ModelObject):
    def __init__(self, model, name, url):
        super().__init__(model, model.agents, name)

        self.url = url
        self.jobs = list()

    def update(self):
        raise NotImplementedError()

    def render_data(self):
        data = super().render_data()
        data["url"] = self.url

        return data
    
class Job(_ModelObject):
    def __init__(self, model, group, component, environment, agent, name):
        super().__init__(model, model.jobs, name)

        assert isinstance(group, Group), group
        assert isinstance(component, Component), component
        assert isinstance(environment, Environment), environment
        assert isinstance(agent, Agent), agent
        assert isinstance(name, str), name

        self.group = group
        self.component = component
        self.environment = environment
        self.agent = agent

        self.group.jobs.append(self)
        self.component.jobs.append(self)
        self.environment.jobs.append(self)
        self.agent.jobs.append(self)

        self.results = _collections.deque(maxlen=2)

    def update(self, context):
        try:
            data = self.fetch_data(context)
        except:
            _log.warn("Failure fetching data for {}".format(self))
            return

        assert data is not None
            
        try:
            result = self.convert_result(data)
        except:
            _log.exception("Failure converting {}".format(self))
            return

        assert result is not None

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

    def render_data(self):
        data = super().render_data()

        data["group_id"] = self.group.id
        data["component_id"] = self.component.id
        data["environment_id"] = self.environment.id
        data["agent_id"] = self.agent.id
        data["url"] = self.url

        data["previous_result"] = None
        data["current_result"] = None

        if self.previous_result:
            data["previous_result"] = self.previous_result.render_data()

        if self.current_result:
            data["current_result"] = self.current_result.render_data()

        return data

    def pprint(self):
        data = self.render_data()
        _pprint.pprint(data)

class JobResult:
    def __init__(self):
        self.number = None
        self.status = None
        self.timestamp = None
        self.duration = None
        self.url = None

    def render_data(self):
        data = dict()
        data["number"] = self.number
        data["status"] = self.status
        data["timestamp"] = self.timestamp
        data["duration"] = self.duration
        data["url"] = self.url
        
        return data

class HttpAgent(Agent):
    def update(self):
        with _requests.Session() as session:
            for job in self.jobs:
                job.update(session)

class HttpJob(Job):
    def fetch_data(self, session, headers=None):
        response = session.get(self.url, headers=headers)

        if response.status_code != 200:
            _log.warn("Request URL:      {}".format(self.url))
            _log.warn("Request headers:  {}".format(headers))
            _log.warn("Response code:    {}".format(response.status_code))
            _log.warn("Response headers: {}".format(response.headers))
            _log.warn("Response text:    {}".format(response.text))

        data = response.json()

        return data
