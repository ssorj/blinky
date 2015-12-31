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

_log = _logging.getLogger("blinky.appveyor")

class AppveyorAgent(HttpAgent):
    html_url = "https://ci.appveyor.com"
    data_url = "https://ci.appveyor.com"

class AppveyorJob(HttpJob):
    def __init__(self, model, group, component, environment, agent, name,
                 account, project, branch):
        super().__init__(model, group, component, environment, agent, name)

        self.account = account
        self.project = project
        self.branch = branch

        self.html_url = "{}/project/{}/{}" \
            .format(self.agent.html_url, self.account, self.project)
        self.data_url = "{}/api/projects/{}/{}/branch/{}" \
            .format(self.agent.data_url, self.account, self.project, self.branch)

    def convert_result(self, data):
        data = data["build"]

        status = data["status"]
        status = _status_mapping.get(status, status)

        timestamp = data["started"]
        timestamp = timestamp[:26]
        timestamp = _datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        timestamp = _calendar.timegm(timestamp.timetuple())

        version = data["version"]
        html_url = "{}/project/{}/{}/build/{}" \
                   .format(self.agent.html_url, self.account, self.project, version)
        
        result = JobResult()
        result.number = data["buildNumber"]
        result.status = status
        result.timestamp = timestamp
        result.duration = None
        result.html_url = html_url

        return result

_status_mapping = {
    "success": "SUCCESS",
    "failed": "FAILURE",
}
