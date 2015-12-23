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

from .common import *

import BlinkyTape as _blinkytape
import requests as _requests
import threading as _threading
import time as _time

_log = logger("blinky.tape")

class Tape:
    def __init__(self, device, url):
        self.device = device
        self.url = url

        self.lights = [_black for i in range(60)]
        self.tape = None

        self.update_thread = _TapeUpdateThread(self)

    def __enter__(self):
        self.tape = _blinkytape.BlinkyTape(self.device, buffered=False)

    def __exit__(self, type, value, traceback):
        self.tape.close()

    def update(self):
        self.lights[59] = _black
        
        try:
            with _requests.Session() as session:
                data = session.get(self.url).json()
        except Exception as e:
            _log.warn("Failure requesting new data; %s", e)
            self.lights[59] = _blinky_yellow
            return

        self.update_lights(data)

    def update_lights(self, data):
        index = 0

        for group_id in sorted(data["test_groups"]):
            group = data["test_groups"][str(group_id)]
            
            for test_id in group["test_ids"]:
                test = data["tests"][str(test_id)]

                for job_id in sorted(test["job_ids"]):
                    job = data["jobs"][str(job_id)]
                    
                    if index >= 58:
                        return

                    self.lights[index] = _Light.for_job(job)

                    index += 1

            index +=1

    def run(self):
        while True:
            self.tick()

    def tick(self):
        colors = [_black.color() for x in range(60)]

        for i, light in enumerate(self.lights):
            if not light.blinky:
                colors[i] = light.color()

        self.tape.send_list(colors)

        _time.sleep(2.9)

        for i, light in enumerate(self.lights):
            colors[i] = light.color()

        self.tape.send_list(colors)

        _time.sleep(0.1)

class _TapeUpdateThread(_threading.Thread):
    def __init__(self, tape):
        super().__init__()

        self.tape = tape
        self.name = "_TapeUpdateThread"
        self.daemon = True

    def start(self):
        _log.info("Starting update thread")
        
        super().start()
        
    def run(self):
        while True:
            _time.sleep(10)

            try:
                self.tape.update()
            except:
                _log.exception("Update failed")

class _Light(object):
    def __init__(self, red, green, blue, blinky=False):
        self.red = red
        self.green = green
        self.blue = blue

        self.blinky = blinky

    def color(self):
        return (self.red, self.green, self.blue)

    @staticmethod
    def for_job(job):
        current_result = job["current_result"]
        previous_result = job["previous_result"]
        
        if current_result is None:
            return _black
        
        if current_result["status"] == "SUCCESS":
            return _green

        if current_result["status"] == "FAILURE":
            if previous_result and previous_result["status"] == "SUCCESS":
                return _blinky_red
            
            return _red

        if current_result["status"] == "UNSTABLE":
            if previous_result and previous_result["status"] == "STABLE":
                return _blinky_red
            
            return _red

        return _gray

_black = _Light(0, 0, 0)
_white = _Light(254, 254, 254)
_gray = _Light(30, 30, 30)

_red = _Light(90, 0, 0)
_green = _Light(30, 60, 0)
_blue = _Light(0, 30, 60)
_yellow = _Light(45, 45, 0)

_blinky_red = _Light(90, 0, 0, True)
_blinky_green = _Light(30, 60, 0, True)
_blinky_blue = _Light(0, 30, 60, True)
_blinky_yellow = _Light(45, 45, 0, True)
