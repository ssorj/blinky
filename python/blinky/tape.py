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
import os as _os
import requests as _requests
import sched as _sched
import serial as _serial
import threading as _threading
import time as _time

_log = _logging.getLogger("blinky.tape")

class BlinkyTape:
    def __init__(self, device_file, data_url):
        self.device = _Device(self, device_file)
        self.data_url = data_url

        self.debug = "BLINKY_DEBUG" in _os.environ
        self.reverse_lights = False

        self.lights = [_black for i in range(60)]

        self.update_thread = _UpdateThread(self)

    def update(self):
        self.lights[59] = _black

        try:
            with _requests.Session() as session:
                data = session.get(self.data_url).json()
        except Exception as e:
            _log.warn("Failure requesting new data: {}".format(str(e)))
            self.lights[59] = _blinky_yellow
            return

        self.update_lights(data)

    def update_lights(self, data):
        _log.info("Updating lights")

        lights = self._convert_data(data)

        if self.reverse_lights:
            lights.reverse()

        self.lights = lights

    def _convert_data(self, data):
        lights = [_black for i in range(60)]
        index = 0

        for group_id in sorted(data["groups"]):
            group = data["groups"][str(group_id)]

            for job_id in group["job_ids"]:
                if index >= 59:
                    return lights

                job = data["jobs"][str(job_id)]
                lights[index] = _Light.for_job(job)
                index += 1

            index +=1

        return lights

    def run(self):
        self.update_thread.start()

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
            _time.sleep(2.9)
            self.blink()
            _time.sleep(0.1)

    def tick(self):
        if self.debug:
            chars = [x.char for x in self.lights]
            print("".join(chars))

        colors = [x.color for x in self.lights]

        self.send_colors(colors)

    def blink(self):
        colors = [_black.color if x.blinky else x.color for x in self.lights]

        self.send_colors(colors)

    def send_colors(self, colors):
        if self.debug:
            chars = list()

            for color in colors:
                if color == (90, 0, 0):
                    chars.append("r")
                elif color == (30, 60, 0):
                    chars.append("g")
                elif color == (0, 0, 0):
                    chars.append(" ")
                else:
                    chars.append("o")

                _red = _Light(90, 0, 0, "r")
                _green = _Light(30, 60, 0, "g")

            print("".join(chars))

        data = [chr(r) + chr(g) + chr(b) for r, g, b in colors] + [chr(255)]
        data = "".join(data)
        data = _codecs.latin_1_encode(data)[0]

        if self.device.serial is not None:
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
        self.scheduler.enter(60, 1, self.update_tape)

        try:
            self.tape.update()
        except:
            _log.exception("Update failed")

class _Device:
    def __init__(self, tape, path):
        self.tape = tape
        self.path = path

        self.serial = None

    def __enter__(self):
        try:
            self.serial = _serial.Serial(self.path, 115200)
        except:
            if not self.tape.debug:
                raise

    def __exit__(self, type, value, traceback):
        if self.serial is not None:
            self.serial.close()

class _Light:
    def __init__(self, red, green, blue, char, blinky=False):
        self.red = red
        self.green = green
        self.blue = blue
        self.char = char

        self.blinky = blinky

        self.color = self.red, self.green, self.blue

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

_black = _Light(0, 0, 0, " ")
_white = _Light(254, 254, 254, "w")
_gray = _Light(30, 30, 30, "a")

_red = _Light(90, 0, 0, "r")
_green = _Light(30, 60, 0, "g")
_blue = _Light(0, 30, 60, "b")
_yellow = _Light(45, 45, 0, "y")

_blinky_red = _Light(90, 0, 0, "R", True)
_blinky_green = _Light(30, 60, 0, "G", True)
_blinky_blue = _Light(0, 30, 60, "B", True)
_blinky_yellow = _Light(45, 45, 0, "Y", True)
