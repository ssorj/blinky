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
import requests as _requests
from datetime import datetime as _datetime

_log = logger("blinky.appveyor")

class AppveyorAgent(HttpAgent):
    pass

class AppveyorJob(HttpJob):
    def __init__(self, model, agent, test, environment, account, project,
                 branch):
        super().__init__(model, agent, test, environment)

        self.account = account
        self.project = project
        self.branch = branch
        self.name = "{}/{}/{}".format(self.account, self.project, self.branch)

        args = self.agent.url, self.account, self.project, self.branch
        self.url = "{}/api/projects/{}/{}/branch/{}".format(*args)

    def convert_result(self, data):
        data = data["build"]

        status = data["status"]
        status = _status_mapping.get(status, status)

        timestamp = data["started"]
        timestamp = timestamp[:26]
        timestamp = _datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        timestamp = _calendar.timegm(timestamp.timetuple())

        version = data["version"]
        args = self.account, self.project, version
        url = "https://ci.appveyor.com/project/{}/{}/build/{}".format(*args)
        
        result = TestResult()
        result.number = data["buildNumber"]
        result.status = status
        result.timestamp = timestamp
        result.duration = None
        result.url = url

        return result

_status_mapping = {
    "success": "SUCCESS",
    "failed": "FAILURE",
}
        
# curl https://ci.appveyor.com/api/projects/ke4qqq/qpid-proton/branch/master

# {
#   "project": {
#     "projectId": 118689,
#     "accountId": 20574,
#     "accountName": "ke4qqq",
#     "builds": [
      
#     ],
#     "name": "qpid-proton",
#     "slug": "qpid-proton",
#     "repositoryType": "gitHub",
#     "repositoryScm": "git",
#     "repositoryName": "apache\/qpid-proton",
#     "repositoryBranch": "master",
#     "isPrivate": false,
#     "skipBranchesWithoutAppveyorYml": false,
#     "enableSecureVariablesInPullRequests": false,
#     "enableDeploymentInPullRequests": false,
#     "rollingBuilds": false,
#     "nuGetFeed": {
#       "id": "qpid-proton-6cv8h7890gk9",
#       "name": "Project qpid-proton",
#       "publishingEnabled": false,
#       "created": "2015-05-14T16:26:53.2545884+00:00"
#     },
#     "securityDescriptor": {
#       "accessRightDefinitions": [
#         {
#           "name": "View",
#           "description": "View"
#         },
#         {
#           "name": "RunBuild",
#           "description": "Run build"
#         },
#         {
#           "name": "Update",
#           "description": "Update settings"
#         },
#         {
#           "name": "Delete",
#           "description": "Delete project"
#         }
#       ],
#       "roleAces": [
#         {
#           "roleId": 30361,
#           "name": "Administrator",
#           "isAdmin": true,
#           "accessRights": [
#             {
#               "name": "View",
#               "allowed": true
#             },
#             {
#               "name": "RunBuild",
#               "allowed": true
#             },
#             {
#               "name": "Update",
#               "allowed": true
#             },
#             {
#               "name": "Delete",
#               "allowed": true
#             }
#           ]
#         },
#         {
#           "roleId": 30362,
#           "name": "User",
#           "isAdmin": false,
#           "accessRights": [
#             {
#               "name": "View"
#             },
#             {
#               "name": "RunBuild"
#             },
#             {
#               "name": "Update"
#             },
#             {
#               "name": "Delete"
#             }
#           ]
#         }
#       ]
#     },
#     "created": "2015-05-14T16:26:51.4888843+00:00",
#     "updated": "2015-05-14T16:29:57.5102415+00:00"
#   },
#   "build": {
#     "buildId": 1807031,
#     "jobs": [
#       {
#         "jobId": "s8ukdpyagk9dlfip",
#         "name": "",
#         "allowFailure": false,
#         "messagesCount": 0,
#         "compilationMessagesCount": 6,
#         "compilationErrorsCount": 0,
#         "compilationWarningsCount": 6,
#         "testsCount": 0,
#         "passedTestsCount": 0,
#         "failedTestsCount": 0,
#         "artifactsCount": 0,
#         "status": "success",
#         "started": "2015-11-06T20:44:55.4907482+00:00",
#         "finished": "2015-11-06T20:48:20.8445433+00:00",
#         "created": "2015-11-06T20:44:51.7421187+00:00",
#         "updated": "2015-11-06T20:48:20.8445433+00:00"
#       }
#     ],
#     "buildNumber": 394,
#     "version": "0.10-SNAPSHOT-master.394",
#     "message": "PROTON-1005: remove references to ANONYMOUS-RELAY",
#     "branch": "master",
#     "isTag": false,
#     "commitId": "a8c94739922524fde4891d59114ea3919cfd96ba",
#     "authorName": "Gordon Sim",
#     "committerName": "Gordon Sim",
#     "committed": "2015-11-06T20:22:23+00:00",
#     "messages": [
      
#     ],
#     "status": "success",
#     "started": "2015-11-06T20:44:55.5063671+00:00",
#     "finished": "2015-11-06T20:48:21.2976661+00:00",
#     "created": "2015-11-06T20:44:50.4608812+00:00",
#     "updated": "2015-11-06T20:48:21.2976661+00:00"
#   }
# }
