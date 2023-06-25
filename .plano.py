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

from bullseye import *

project.name = "blinky"
project.data_dirs = ["static"]

image_registry = "quay.io"
image_tag = f"{image_registry}/ssorj/blinky"

@command
def test_(*args, **kwargs):
    with project_env():
        run("blinky --config misc/config.py --init-only")

@command
def run_():
    """Run the server"""

    clean()
    build()

    with project_env():
        run("blinky --config misc/config.py")

@command
def build_image(clean=False):
    """Build a container image"""

    if clean:
        clean_image()

    run(f"podman build -t {image_tag} .")

def _maybe_build_image(clean):
    if clean:
        clean_image()

    if run(f"podman image inspect {image_tag}", check=False, output=DEVNULL).exit_code != 0:
        build_image()

@command
def run_image(clean=False):
    """Run the container image"""

    _maybe_build_image(clean)

    run(f"podman run --rm -p 8080:8080 {image_tag}")

@command
def debug_image(clean=False):
    """Run the container image in debug mode"""

    _maybe_build_image(clean)

    run(f"podman run --rm -p 8080:8080 -it {image_tag} /bin/bash")

@command
def test_image(clean=False):
    """Test the container image"""

    _maybe_build_image(clean)

    run(f"podman run --rm -p 8080:8080 -it {image_tag} blinky --init-only")

@command
def clean_image():
    """Delete the container image"""
    run(f"podman image rm {image_tag}", check=False)

@command
def registry_login():
    """Log in to the image registry"""
    run(f"podman login {image_registry}")

@command
def push_image():
    """Push the image to the image registry"""

    registry_login()

    run(f"podman push {image_tag}")

@command
def big_test():
    """Run all the tests I have"""

    test()
    test_image(clean=True)
