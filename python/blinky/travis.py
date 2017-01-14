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

import calendar as _calendar
import logging as _logging
import requests as _requests

from datetime import datetime as _datetime

_log = _logging.getLogger("blinky.travis")

_status_mapping = {
    "passed": PASSED,
    "failed": FAILED,
}

class TravisAgent(HttpAgent):
    def __init__(self, model, name):
        super().__init__(model, name)

        self.html_url = "https://travis-ci.org"
        self.data_url = "https://api.travis-ci.org"

class TravisJob(HttpJob):
    def __init__(self, model, group, component, environment, agent, name,
                 repo, branch):
        super().__init__(model, group, component, environment, agent, name)

        self.repo = repo
        self.branch = branch

        self.html_url = "{}/repos/{}/branches/{}" \
            .format(self.agent.html_url, self.repo, self.branch)
        self.data_url = "{}/repos/{}/branches/{}" \
            .format(self.agent.data_url, self.repo, self.branch)

    def fetch_data(self, session):
        headers = {
            "User-Agent": "Blinky/0.1",
            "Accept": "application/vnd.travis-ci.2+json",
        }

        return super().fetch_data(session, headers)

    def convert_result(self, data):
        data = data["branch"]

        status = data["state"]
        status = _status_mapping.get(status, status)

        start_time = data["started_at"]

        if start_time is not None:
            start_time = _datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
            start_time = _calendar.timegm(start_time.timetuple())

        html_url = "https://travis-ci.org/{}/builds/{}".format(self.repo, data["id"])

        result = JobResult()
        result.number = int(data["number"])
        result.status = status
        result.start_time = start_time
        result.duration = data["duration"]
        result.html_url = html_url

        return result
