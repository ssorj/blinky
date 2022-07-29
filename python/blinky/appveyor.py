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

from .model import *

import logging as _logging

_log = _logging.getLogger("blinky.appveyor")

_status_mapping = {
    "success": PASSED,
    "failed": FAILED,
}

class AppVeyorAgent(HttpAgent):
    def __init__(self, model, name):
        super().__init__(model, name)

        self.html_url = "https://ci.appveyor.com"
        self.data_url = "https://ci.appveyor.com"

class AppVeyorJob(HttpJob):
    def __init__(self, model, group, component, environment, agent, name, account, project, branch):
        super().__init__(model, group, component, environment, agent, name)

        self.account = account
        self.project = project
        self.branch = branch

        self.html_url = f"{self.agent.html_url}/project/{self.account}/{self.project}"
        self.data_url = f"{self.agent.html_url}/api/projects/{self.account}/{self.project}/branch/{self.branch}"

    def convert_run(self, data):
        data = data["build"]

        status = data["status"]
        status = _status_mapping.get(status, status)

        start_time = data.get("started")

        if start_time is None:
            start_time = data["created"]

        start_time = parse_timestamp(start_time[:23], "%Y-%m-%dT%H:%M:%S.%f")

        version = data["version"]

        html_url = f"{self.html_url}/build/{version}"
        data_url = f"{self.agent.data_url}/api/projects/{self.account}/{self.project}/build/{version}"
        tests_url = None

        try:
            tests = data["jobs"][0]["testsCount"]
        except:
            tests = 0

        if tests > 0:
            tests_url = f"{self.html_url}/build/tests"

        run = JobRun()
        run.number = data["buildNumber"]
        run.status = status
        run.start_time = start_time
        run.duration = None
        run.html_url = html_url
        run.data_url = data_url
        run.tests_url = tests_url

        return run
