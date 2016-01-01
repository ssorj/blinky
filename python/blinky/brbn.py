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

import brbn as _brbn
import datetime as _datetime
import json as _json
import logging as _logging
import os as _os
import requests as _requests
import sys as _sys
import time as _time

_log = _logging.getLogger("blinky.brbn")

class Blinky(_brbn.Application):
    def __init__(self, home, model):
        super().__init__(home)
        
        self.model = model

        _Data(self, "/data.json")
        _Proxy(self, "/proxy")

class _Data(_brbn.Resource):
    def get_etag(self, request):
        return self.app.model.json_digest
    
    def render(self, request):
        return self.app.model.json

class _Proxy(_brbn.Resource):
    def process(self, request):
        url = request.require("url")

        if url == "/data.json":
            request.proxied_content = self.app.resources[url].render(request)
            request.proxied_content_type = "application/json"
        else:
            response = _requests.get(url)
            request.proxied_content = response.text
            request.proxied_content_type = response.headers["content-type"]

    def get_content_type(self, request):
        return request.proxied_content_type

    def render(self, request):
        return request.proxied_content
