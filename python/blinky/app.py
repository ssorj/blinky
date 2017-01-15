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
import re as _re
import requests as _requests
import sys as _sys
import time as _time

_log = _logging.getLogger("blinky.app")

class Blinky(_brbn.Application):
    def __init__(self, home, model):
        super().__init__(home)

        self.model = model

        _Data(self, "/data.json")
        _Errors(self, "/errors.html")
        _Proxy(self, "/proxy")

class _Data(_brbn.Resource):
    def get_etag(self, request):
        return self.app.model.json_digest

    def render(self, request):
        return self.app.model.json

class _Errors(_brbn.Resource):
    def process(self, request):
        url = request.require("url")

        response = _requests.get(url)
        request.proxied_content = response.text

    def render(self, request):
        pass

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

_lines_before = 5
_lines_after = 20

_error_expr = _re.compile(r"(^|\s|\*)(error|fail|failed|failure|timeout)s?($|\s|:)", _re.IGNORECASE)

def _find_error_windows(lines):
    matching_lines = list()

    for index, line in enumerate(lines):
        if _re.search(_error_expr, line):
            matching_lines.append(index)

    # Filter out known false positives

    filtered_lines = list()

    for index in matching_lines:
        line = lines[index]

        if "Failures: 0, Errors: 0" in line:
            continue

        if "-- Performing Test" in line:
            continue

        if "timeout=" in line:
            continue

        if "Test timeout computed to be" in line:
            continue

        filtered_lines.append(index)

    # Compute windows

    windows = list()

    for index in filtered_lines:
        start = max(0, index - _lines_before)
        end = min(len(lines), index + _lines_after)

        windows.append((start, end))

    # Collapse overlapping windows

    collapsed_windows = list()
    collapsed_window = None

    for window in windows:
        if collapsed_window is None:
            collapsed_window = window

        if window[0] < collapsed_window[1]:
            collapsed_window = collapsed_window[0], window[1]
        else:
            collapsed_windows.append(collapsed_window)
            collapsed_window = window

    if collapsed_window is not None:
        collapsed_windows.append(collapsed_window)

    # for window in windows:
    #     print("w", window)

    # for window in collapsed_windows:
    #     print("c", window)

    return collapsed_windows
