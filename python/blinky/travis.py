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

import calendar as _calendar
import requests as _requests

from datetime import datetime as _datetime

_log = logger("blinky.travis")

class TravisAgent(HttpAgent):
    pass

class TravisJob(HttpJob):
    def __init__(self, model, agent, test, environment, repo, branch):
        super().__init__(model, agent, test, environment)

        self.repo = repo
        self.branch = branch
        self.name = "{}/{}".format(self.repo, self.branch)

        args = self.agent.url, self.repo, self.branch
        self.url = "{}/repos/{}/branches/{}".format(*args)

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

        timestamp = data["started_at"]
        timestamp = _datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        timestamp = _calendar.timegm(timestamp.timetuple())

        build_id = data["id"]
        url = "https://travis-ci.org/{}/builds/{}".format(self.repo, build_id)
        
        result = TestResult()
        result.number = int(data["number"])
        result.status = status
        result.timestamp = timestamp
        result.duration = data["duration"]
        result.url = url

        return result

_status_mapping = {
    "passed": "SUCCESS",
    "failed": "FAILURE",
}
        
# [jross@office blinky]$ curl -H "Accept: application/vnd.travis-ci.2+json" https://api.travis-ci.org/repos/apache/qpid-proton
# {"repo":{
#    "id":3331825,
#    "slug":"apache/qpid-proton",
#    "active":true,
#    "description":"Mirror of Apache Qpid Proton",
#    "last_build_id":88411503,
#    "last_build_number":"401",
#    "last_build_state":"passed",
#    "last_build_duration":668,
#    "last_build_language":null,
#    "last_build_started_at":"2015-10-30T19:11:43Z",
#    "last_build_finished_at":"2015-10-30T19:22:51Z",
#    "github_language":"Java"
#    }}

# {
#   "branch": {
#     "id": 89301459,
#     "repository_id": 3331825,
#     "commit_id": 25391617,
#     "number": "418",
#     "config": {
#       "os": [
#         "linux"
#       ],
#       "sudo": false,
#       "language": "python",
#       "python": [
#         2.7
#       ],
#       "addons": {
#         "apt": {
#           "packages": [
#             "cmake",
#             "libssl-dev",
#             "libsasl2-dev",
#             "sasl2-bin",
#             "swig",
#             "python-dev",
#             "valgrind",
#             "ruby",
#             "ruby-dev",
#             "python3-dev",
#             "php5",
#             "openjdk-7-jdk"
#           ]
#         }
#       },
#       "install": [
#         "pip install --upgrade pip",
#         "pip install tox",
#         "gem install rspec simplecov",
#         "gem install minitest --version 4.7.0"
#       ],
#       "before_script": [
#         "export PATH=${HOME}\/.local\/bin:${PATH}",
#         "mkdir Build",
#         "cd Build",
#         "cmake .. -DCMAKE_INSTALL_PREFIX=$PWD\/install"
#       ],
#       "script": [
#         "cmake --build . --target install && ctest -V"
#       ],
#       ".result": "configured"
#     },
#     "state": "passed",
#     "started_at": "2015-11-04T20:16:14Z",
#     "finished_at": "2015-11-04T20:28:55Z",
#     "duration": 761,
#     "job_ids": [
#       89301460
#     ],
#     "pull_request": false
#   },
#   "commit": {
#     "id": 25391617,
#     "sha": "07dc168b577f88921e97f3b6874741583e93e345",
#     "branch": "master",
#     "message": "PROTON-1040: ensure timeout is never None",
#     "committed_at": "2015-11-04T20:11:14Z",
#     "author_name": "Gordon Sim",
#     "author_email": "gsim@redhat.com",
#     "committer_name": "Gordon Sim",
#     "committer_email": "gsim@redhat.com",
#     "compare_url": "https:\/\/github.com\/apache\/qpid-proton\/compare\/c0917a0fbc74...07dc168b577f"
#   }
# }
