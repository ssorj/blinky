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

_log = _logging.getLogger("blinky.gitlab")

_status_mapping = {
    "success": PASSED,
    "failure": FAILED,
}

class GitLabAgent(HttpAgent):
    def __init__(self, model, name, base_url="gitlab.com", token=None):
        super().__init__(model, name)

        self.html_url = f"https://{base_url}"
        self.data_url = f"https://{base_url}/api/v4"
        self.token = token

class GitLabJob(HttpJob):
    def __init__(self, model, group, component, environment, agent, name, repo, branch):
        super().__init__(model, group, component, environment, agent, name)

        self.repo = repo
        self.branch = branch

        escaped_repo_name = _parse.quote(self.repo, safe="")

        self.html_url = f"{self.agent.html_url}/{self.repo}/-/pipelines?ref={self.branch}"
        self.data_url = f"{self.agent.data_url}/projects/{escaped_repo_name}/pipelines/latest?ref={self.branch}"

    def convert_result(self, data):
        timestamp_format = "%Y-%m-%dT%H:%M:%S.%fZ"

        status = data["status"]
        status = _status_mapping.get(status, status)

        start_time = parse_timestamp(data["created_at"], timestamp_format)

        end_time = None
        duration = None

        if data["status"] != "running":
            end_time = parse_timestamp(data["updated_at"], timestamp_format)
            duration = end_time - start_time

        result = JobResult()
        result.number = data["iid"]
        result.status = status
        result.start_time = start_time
        result.duration = duration
        result.html_url = data["web_url"]
        result.data_url = f"{self.agent.data_url}/projects/{data['project_id']}/pipelines/{data['id']}"

        return result
