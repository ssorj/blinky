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

_log = _logging.getLogger("blinky.circle")

_status_mapping = {
    "success": PASSED,
    "failed": FAILED,
}

class CircleAgent(HttpAgent):
    def __init__(self, model, name):
        super().__init__(model, name)

        self.html_url = "https://circleci.com"
        self.data_url = "https://circleci.com"

class CircleJob(HttpJob):
    def __init__(self, model, group, component, environment, agent, name, repo, branch):
        super().__init__(model, group, component, environment, agent, name)

        self.repo = repo
        self.branch = branch

        self.html_url = f"{self.agent.html_url}/{self.repo}/tree/{self.branch}"
        self.data_url = f"{self.agent.data_url}/api/v1.1/project/{self.repo}/tree/{self.branch}?limit=1&shallow=1"

    def convert_result(self, data):
        data = data[0]
        number = data["build_num"]

        status = data["status"]
        status = _status_mapping.get(status, status)

        start_time = data["start_time"]

        if start_time is None:
            start_time = data["queued_at"]

        start_time = parse_timestamp(start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        stop_time = parse_timestamp(data["stop_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
        duration = None

        if stop_time is not None:
            duration = stop_time - start_time

        html_url = data["build_url"]
        data_url = f"{self.agent.data_url}/api/v1.1/project/{self.repo}/{number}?limit=1&shallow=1"

        result = JobResult()
        result.number = number
        result.status = status
        result.start_time = start_time
        result.duration = duration
        result.html_url = html_url
        result.data_url = data_url

        return result
