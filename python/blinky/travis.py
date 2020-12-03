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

_log = _logging.getLogger("blinky.travis")

_status_mapping = {
    "passed": PASSED,
    "failed": FAILED,
    "errored": FAILED,
}

class TravisAgent(HttpAgent):
    def __init__(self, model, name,
                 html_url="https://travis-ci.com",
                 data_url="https://api.travis-ci.com",
                 token=None):
        super().__init__(model, name)

        self.html_url = html_url
        self.data_url = data_url
        self.token = token

class TravisJob(HttpJob):
    def __init__(self, model, group, component, environment, agent, name, repo, branch):
        super().__init__(model, group, component, environment, agent, name)

        self.repo = repo
        self.branch = branch

        self.html_url = f"{self.agent.html_url}/{self.repo}/branches"
        self.data_url = f"{self.agent.data_url}/repos/{self.repo}/branches/{self.branch}"

    def fetch_data(self, session):
        headers = {
            "User-Agent": "Blinky/0.1",
            "Accept": "application/vnd.travis-ci.2+json",
        }

        return super().fetch_data(session, headers)

    def convert_result(self, data):
        data = data["branch"]
        build_id = data["id"]

        status = data["state"]
        status = _status_mapping.get(status, status)

        start_time = parse_timestamp(data["started_at"])
        duration = data["duration"]

        if duration is not None:
            duration = int(round(duration * 1000))

        html_url = f"{self.agent.html_url}/{self.repo}/builds/{build_id}"
        data_url = f"{self.agent.data_url}/builds/{build_id}"

        result = JobResult()
        result.number = int(data["number"])
        result.status = status
        result.start_time = start_time
        result.duration = duration
        result.html_url = html_url
        result.data_url = data_url

        return result
