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

import codecs as _codecs
import logging as _logging
import requests as _requests
import sched as _sched
import serial as _serial
import threading as _threading
import time as _time

_log = _logging.getLogger("blinky.tape")

class BlinkyTape:
    def __init__(self, device_path, url):
        self.device = _Device(device_path)
        self.url = url

        self.lights = [_black for i in range(60)]
        self.scheduler = _sched.scheduler()

        self.update_thread = _UpdateThread(self)

    def update(self):
        self.lights[59] = _black
        
        try:
            with _requests.Session() as session:
                data = session.get(self.url).json()
        except Exception as e:
            _log.warn("Failure requesting new data: {}".format(str(e)))
            self.lights[59] = _blinky_yellow
            return

        self.update_lights(data)

    def update_lights(self, data):
        index = 0

        for group_id in sorted(data["groups"]):
            group = data["groups"][str(group_id)]

            for job_id in group["job_ids"]:
                job = data["jobs"][str(job_id)]

                if index >= 58:
                    return

                self.lights[index] = _Light.for_job(job)

                index += 1

            index +=1

    def run(self):
        while True:
            try:
                self.do_run()
            except KeyboardInterrupt:
                raise
            except:
                _log.exception("Error!")
                _time.sleep(5)
            
    def do_run(self):
        with self.device:
            self.tick()
            self.scheduler.run()

    def tick(self):
        self.scheduler.enter(0.1, 1, self.blink)

        colors = [x.color() for x in self.lights]

        self.send_colors(colors)

    def blink(self):
        self.scheduler.enter(2.9, 1, self.tick)

        colors = [_black.color() if x.blinky else x.color() for x in self.lights]

        self.send_colors(colors)

    def send_colors(self, colors):
        data = [chr(r) + chr(g) + chr(b) for r, g, b in colors]
        data.append(chr(255)) # Control

        data = "".join(data)
        data = _codecs.latin_1_encode(data)[0]

        self.device.serial.write(data)
        self.device.serial.flush()
        self.device.serial.flushInput()

class _UpdateThread(_threading.Thread):
    def __init__(self, tape):
        super().__init__()

        self.tape = tape
        self.name = "update"
        self.daemon = True
        self.scheduler = _sched.scheduler()

    def start(self):
        _log.info("Starting update thread")
        
        super().start()
        
    def run(self):
        self.update_tape()
        self.scheduler.run()

    def update_tape(self):
        self.scheduler.enter(30, 1, self.update_tape)

        try:
            self.tape.update()
        except:
            _log.exception("Update failed")

class _Device:
    def __init__(self, path):
        self.path = path
        self.serial = None

    def __enter__(self):
        self.serial = _serial.Serial(self.path, 115200)

    def __exit__(self, type, value, traceback):
        self.serial.close()

class _Light:
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
        
        if current_result["status"] == "PASSED":
            return _green

        if current_result["status"] == "FAILED":
            if previous_result and previous_result["status"] == "PASSED":
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
