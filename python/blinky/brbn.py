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
import sys as _sys
import time as _time

_log = _logging.getLogger("blinky.brbn")

_http_date = "%a, %d %b %Y %H:%M:%S %Z"

class Blinky(_brbn.Application):
    def __init__(self, home, model):
        super().__init__(home)
        
        self.model = model

        _Data(self, "/data.json")

class _Data(_brbn.Resource):
    def get_etag(self, request):
        return str(self.app.model.update_time)
    
    def render(self, request):
        data = self.app.model.render_data()
        return _json.dumps(data, indent=4, separators=(", ", ": "))

    def xxx_send_response(self, request):
        ims_timestamp = request.env.get("HTTP_IF_MODIFIED_SINCE")
        update_time = self.app.model.update_time

        if ims_timestamp is not None and update_time is not None:
            update_time = update_time.replace(microsecond=0)
            ims_time = _datetime.datetime.strptime(ims_timestamp, _http_date)

            # _log.info("304 if updated {} <= IMS {}".format(update_time, ims_time))

            if update_time <= ims_time:
                return request.respond_not_modified()

        content = self.app.model.render_data()
        content = _json.dumps(content, indent=4, separators=(", ", ": "))
        content = content.encode("utf-8")

        return request.respond_ok(content, "application/json")
