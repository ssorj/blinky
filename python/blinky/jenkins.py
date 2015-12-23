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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from .model import *

import requests as _requests

_log = logger("blinky.jenkins")

class JenkinsAgent(HttpAgent):
    pass

class JenkinsJob(HttpJob):
    def __init__(self, model, agent, test, environment, name):
        super().__init__(model, agent, test, environment)

        self.name = name

        args = self.agent.url, self.name
        self.url = "{}/job/{}/lastBuild/api/json".format(*args)

    def convert_result(self, data):
        result = TestResult()
        result.number = data["number"]
        result.status = data["result"]
        result.timestamp = data["timestamp"] / 1000.0
        result.duration = data["duration"] / 1000.0
        result.url = data["url"]

        return result
