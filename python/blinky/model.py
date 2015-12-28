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

from faller import logger

import collections as _collections
import datetime as _datetime
import pprint as _pprint
import requests as _requests
import threading as _threading
import time as _time

_log = logger("blinky.model")

class Model:
    def __init__(self):
        self.update_thread = _ModelUpdateThread(self)
        self.update_time = None
        
        self.test_groups = list()
        self.components = list()
        self.environments = list()
        self.tests = list()
        self.agents = list()
        self.jobs = list()

    def __repr__(self):
        cls = self.__class__.__name__
        return "{}({})".format(cls, id(self))

    def render_data(self):
        data = dict()

        if self.update_time is None:
            raise Exception("The model isn't updated yet")

        time = self.update_time.timetuple()
        time = _time.mktime(time) + 1e-6 * self.update_time.microsecond

        data["update_timestamp"] = time
        
        test_groups_data = data["test_groups"] = dict()
        components_data = data["components"] = dict()
        environments_data = data["environments"] = dict()
        tests_data = data["tests"] = dict()
        agents_data = data["agents"] = dict()
        jobs_data = data["jobs"] = dict()
        
        for test_group in self.test_groups:
            test_groups_data[test_group.id] = test_group.render_data()

        for component in self.components:
            components_data[component.id] = component.render_data()

        for environment in self.environments:
            environments_data[environment.id] = environment.render_data()

        for test in self.tests:
            tests_data[test.id] = test.render_data()

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
    def __init__(self, model, collection):
        assert isinstance(model, Model), model
        assert isinstance(collection, list), collection
        
        self.model = model

        self.id = len(collection)
        # XXX self.id = "{:04}".format(self.id)

        self.name = None
        
        collection.append(self)

    def __repr__(self):
        cls = self.__class__.__name__
        return "{}({},{})".format(cls, self.id, self.name)

    def render_data(self):
        data = dict()
        data["id"] = self.id

        if hasattr(self, "name"):
            data["name"] = self.name

        if hasattr(self, "tests"):
            data["test_ids"] = [x.id for x in self.tests]
        
        return data
        
class TestGroup(_ModelObject):
    def __init__(self, model, name):
        super().__init__(model, model.test_groups)

        self.name = name
        
        self.tests = list()
        self.tests_by_component = _collections.defaultdict(list)
        
class Component(_ModelObject):
    def __init__(self, model, name):
        super().__init__(model, model.components)

        self.name = name

        self.tests = list()
        self.tests_by_test_group = _collections.defaultdict(list)

class Environment(_ModelObject):
    def __init__(self, model, name):
        super().__init__(model, model.environments)

        self.name = name

class Test(_ModelObject):
    def __init__(self, model, test_group, component, name=None):
        super().__init__(model, model.tests)

        self.name = name
        self.test_group = test_group
        self.component = component

        self.jobs = list()
        
        self.test_group.tests.append(self)
        self.test_group.tests_by_component[self.component].append(self)

        self.component.tests.append(self)
        self.component.tests_by_test_group[self.test_group].append(self)

    def render_data(self):
        data = super().render_data()

        data["test_group_id"] = self.test_group.id
        data["component_id"] = self.component.id
        data["job_ids"] = [x.id for x in self.jobs]

        return data

class Agent(_ModelObject):
    def __init__(self, model, name, url):
        super().__init__(model, model.agents)

        self.name = name
        self.url = url

        self.jobs = list()

    def update(self):
        raise NotImplementedError()

    def render_data(self):
        data = super().render_data()

        data["name"] = self.name
        data["url"] = self.url
        data["job_ids"] = [x.id for x in self.jobs]

        return data
    
class Job(_ModelObject):
    def __init__(self, model, agent, test, environment):
        super().__init__(model, model.jobs)

        assert isinstance(agent, Agent), agent
        assert isinstance(test, Test), test
        assert isinstance(environment, Environment), environment
        
        self.agent = agent
        self.test = test
        self.environment = environment

        self.results = _collections.deque(maxlen=2)

        self.agent.jobs.append(self)
        self.test.jobs.append(self)

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

        data["test_id"] = self.test.id
        data["environment_id"] = self.environment.id
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

class TestResult:
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

def _print_model(model):
    for test_group in model.test_groups:
        print(test_group.name)
        print()
            
        for component in model.components:
            tests = component.tests_by_test_group[test_group]

            for test in tests:
                if test.name is None:
                    print(component.name)
                else:
                    print("{} - {}".format(component.name, test.name))
                
                for job in test.jobs:
                    _print_job(job)

        print()

def _print_job(job):
    name = job.environment.name
    current = _format_result(job.current_result)
    previous = _format_result(job.previous_result)
    
    print("  {:18}  {:18}  {:18}".format(name, current, previous))

def _format_result(result):
    if result is None:
        return "-"

    if result.timestamp is None:
        seconds_ago = "-"
    else:
        seconds_ago = int(_time.time() - result.timestamp / 1000)
        seconds_ago = _format_duration(seconds_ago)

    return "{} {}".format(result.status, seconds_ago)

_minute = 60
_hour = _minute * 60
_day = _hour * 24
_week = _day * 7

def _format_duration(seconds):
    minutes = int(seconds / _minute)
    hours = int(seconds / _hour)
    days = int(seconds / _day)
    weeks = int(seconds / _week)

    if weeks >= 2:
        return "{:2}w".format(weeks)

    if days >= 2:
        return "{:2}d".format(days)

    if hours >= 1:
        return "{:2}h".format(hours)

    if minutes >= 1:
        return "{:2}m".format(minutes)

    return "{:2}s".format(seconds)
