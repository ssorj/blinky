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
import urllib.parse as _parse

_log = _logging.getLogger("blinky.github")

_status_mapping = {
    "success": PASSED,
    "failure": FAILED,
}

class GitHubAgent(HttpAgent):
    def __init__(self, model, name, token=None):
        super().__init__(model, name)

        self.html_url = "https://github.com"
        self.data_url = "https://api.github.com"
        self.token = token

class GitHubJob(HttpJob):
    def __init__(self, model, group, component, environment, agent, name, repo, branch, workflow_name, workflow_id):
        super().__init__(model, group, component, environment, agent, name)

        self.repo = repo
        self.branch = branch
        self.workflow_name = workflow_name
        self.workflow_id = workflow_id

        escaped_name = _parse.quote(self.workflow_name)

        if " " in self.workflow_name:
            escaped_name = f"\"{escaped_name}\""

        self.html_url = f"{self.agent.html_url}/{self.repo}/actions?query=workflow%3A{escaped_name}"
        self.data_url = f"{self.agent.data_url}/repos/{self.repo}/actions/workflows/{self.workflow_id}/runs?branch={self.branch}"

    def convert_result(self, data):
        try:
            data = data["workflow_runs"][0]
        except IndexError:
            raise Exception("No data!")

        status = data["conclusion"]
        status = _status_mapping.get(status, status)

        start_time = parse_timestamp(data["created_at"])

        end_time = None
        duration = None

        if data["status"] == "completed":
            end_time = parse_timestamp(data["updated_at"])
            duration = end_time - start_time

        result = JobResult()
        result.number = data["run_number"]
        result.status = status
        result.start_time = start_time
        result.duration = duration
        result.html_url = data["html_url"]
        result.data_url = data["url"]

        return result
