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

.NOTPARALLEL:

DESTDIR := ""
INSTALL_DIR := ${HOME}/.local/opt/bodega

VIRTUALENV_ENABLED := 1

export BLINKY_HOME = ${CURDIR}/build
export PATH := ${CURDIR}/build/bin:${PATH}
export PYTHONPATH := ${BLINKY_HOME}/python:${CURDIR}/python:${PYTHONPATH}

VERSION := $(shell cat VERSION.txt)

BIN_SOURCES := $(shell find bin -type f -name \*.in)
BIN_TARGETS := ${BIN_SOURCES:%.in=build/%}

MISC_SOURCES := $(shell find misc -type f -name \*.in)
MISC_TARGETS := ${MISC_SOURCES:%.in=build/%}

.PHONY: default
default: build

.PHONY: help
help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "clean          Clean up the source tree"
	@echo "test           Run the tests"
	@echo "run            Run the server"

.PHONY: clean
clean:
	find python -type f -name \*.pyc -delete
	find python -type d -name __pycache__ -delete
	rm -rf build

.PHONY: build
build: ${BIN_TARGETS} ${MISC_TARGETS} build/install-dir.txt
	ln -sfT ../python build/python
	ln -sfT ../static build/static

.PHONY: install
install: build
	scripts/install-files build/bin ${DESTDIR}$$(cat build/install-dir.txt)/bin
	scripts/install-files python ${DESTDIR}$$(cat build/install-dir.txt)/python
	scripts/install-files python/blinky ${DESTDIR}$$(cat build/install-dir.txt)/python/blinky
	scripts/install-files static ${DESTDIR}$$(cat build/install-dir.txt)/static

.PHONY: test
test: build
	scripts/run-tests

.PHONY: run
run: build
	blinky

.PHONY: build-image
build-image:
	sudo docker build -t ssorj/blinky .

.PHONY: test-image
test-image:
	sudo docker run --rm --user 9999 -it ssorj/blinky /app/bin/blinky-test

.PHONY: run-image
run-image:
	sudo docker run --rm --user 9999 -p 8080:8080 ssorj/blinky

.PHONY: debug-image
debug-image:
	sudo docker run --rm --user 9999 -p 8080:8080 -it ssorj/blinky /bin/bash

build/install-dir.txt:
	echo ${INSTALL_DIR} > build/install-dir.txt

build/bin/%: bin/%.in
	scripts/configure-file -a blinky_home=${INSTALL_DIR} $< $@

build/misc/%: misc/%.in
	scripts/configure-file -a blinky_home=${INSTALL_DIR} $< $@

.PHONY: update-gesso
update-gesso:
	curl "https://raw.githubusercontent.com/ssorj/gesso/master/gesso.js" -o files/gesso.js

.PHONY: update-%
update-%:
	curl "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py" -o python/$*.py
