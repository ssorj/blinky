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

from plano import *

@command
def build():
    check_module("build")
    check_module("wheel")

    clean()

    remove("src/brbn/plano")
    copy("subrepos/plano/src/plano", "src/brbn/plano")

    run("python -m build")

@command
def test(verbose=False, coverage=False):
    check_program("pip")
    check_module("venv")

    build()

    wheel = find_wheel()

    with temp_dir() as dir:
        run(f"python -m venv {dir}")
        run(f". {dir}/bin/activate && pip install {wheel}", shell=True)

        path = call(f". {dir}/bin/activate && command -v brbn-self-test", shell=True).strip()
        expected_path = f"{dir}/bin/brbn-self-test"

        assert path == expected_path, (path, expected_path)

        args = list()

        if verbose:
            args.append("--verbose")

        args = " ".join(args)

        if coverage:
            import sys

            # XXX
            with working_env(PYTHONPATH=f"{dir}/lib64/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"):
                run(f". {dir}/bin/activate && coverage run --source brbn {dir}/bin/brbn-self-test {args}", shell=True)

            run("coverage report")
            run("coverage html")

            print(f"file:{get_current_dir()}/htmlcov/index.html")
        else:
            run(f". {dir}/bin/activate && brbn-self-test {args}", shell=True)

@command
def install():
    build()

    wheel = find_wheel()

    run(f"pip install --user --force-reinstall {wheel}")

@command
def clean():
    remove("dist")
    remove("src/brbn/__pycache__")

@command
def upload():
    """
    Upload the package to PyPI
    """

    check_program("twine", "pip install twine")

    build()

    run("twine upload --repository testpypi dist/*", shell=True)

def find_wheel():
    for file in list_dir("dist", "ssorj_brbn-*.whl"):
        return join("dist", file)
    else:
        fail("Wheel file not found")
