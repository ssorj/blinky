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
PREFIX := /usr/local
INSTALLED_BLINKY_HOME = ${PREFIX}/share/blinky

VIRTUALENV_ENABLED := 1

export BLINKY_HOME = ${PWD}/build/blinky
export PATH := ${PWD}/build/bin:${PATH}
export PYTHONPATH := ${BLINKY_HOME}/python:${PWD}/python:${PYTHONPATH}

VERSION := $(shell cat VERSION.txt)

BIN_SOURCES := $(shell find bin -type f -name \*.in)
BIN_TARGETS := ${BIN_SOURCES:%.in=build/%}

MISC_SOURCES := $(shell find misc -type f -name \*.in)
MISC_TARGETS := ${MISC_SOURCES:%.in=build/%}

PYTHON_SOURCES := $(shell find python -type f -name \*.py)
PYTHON_TARGETS := ${PYTHON_SOURCES:%=build/blinky/%} ${PYTHON_SOURCES:%.in=build/blinky/%}

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
build: ${BIN_TARGETS} ${MISC_TARGETS} ${PYTHON_TARGETS} build/prefix.txt
	ln -sfT ../../files build/blinky/files

.PHONY: install
install: build
	scripts/install-files build/bin ${DESTDIR}$$(cat build/prefix.txt)/bin
	scripts/install-files build/blinky ${DESTDIR}$$(cat build/prefix.txt)/share/blinky
	scripts/install-files -n \*.service build/misc ${DESTDIR}${PREFIX}/lib/systemd/system

.PHONY: test
test: build
	scripts/run-tests

.PHONY: run
run: build
	blinky

build/prefix.txt:
	echo ${PREFIX} > build/prefix.txt

build/bin/%: bin/%.in
	scripts/configure-file -a blinky_home=${INSTALLED_BLINKY_HOME} $< $@

build/misc/%: misc/%.in
	scripts/configure-file -a blinky_home=${INSTALLED_BLINKY_HOME} $< $@

build/blinky/python/blinky/%: python/blinky/% python/blinky/model.py python/brbn.py python/pencil.py python/plano.py python/spindle.py
	@mkdir -p ${@D}
	cp $< $@

build/blinky/python/%: python/%
	@mkdir -p ${@D}
	cp $< $@

.PHONY: update-%
update-%:
	curl "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py" -o python/$*.py

# VERSION := $(shell cat VERSION.txt)

# DESTDIR := ""
# PREFIX := /usr/local
# BLINKY_HOME = ${PREFIX}/share/blinky

# export PATH := install/bin:${PATH}
# export PYTHONPATH := python:${PYTHONPATH}

# .PHONY: default
# default: devel

# .PHONY: help
# help:
# 	@echo "build          Build the code"
# 	@echo "install        Install the code"
# 	@echo "clean          Clean up the source tree"
# 	@echo "devel          Build, install, and run in this development session"

# .PHONY: clean
# clean:
# 	find python -type f -name \*.pyc -delete
# 	find python -type d -name __pycache__ -delete
# 	rm -rf build
# 	rm -rf install

# .PHONY: build
# build:
# 	scripts/configure-file -a blinky_home=${BLINKY_HOME} bin/blinky.in build/bin/blinky
# 	scripts/configure-file -a blinky_home=${BLINKY_HOME} bin/blinky-tape.in build/bin/blinky-tape
# 	scripts/configure-file -a PREFIX=${PREFIX} misc/blinky.service.in build/misc/blinky.service
# 	scripts/configure-file -a PREFIX=${PREFIX} misc/blinky-tape.service.in build/misc/blinky-tape.service

# .PHONY: install
# install: build
# 	scripts/install-files -n \*.py python ${DESTDIR}${BLINKY_HOME}/python
# 	scripts/install-files files ${DESTDIR}${BLINKY_HOME}/files
# 	scripts/install-files build/bin ${DESTDIR}${PREFIX}/bin
# 	scripts/install-files -n \*.service build/misc ${DESTDIR}${PREFIX}/lib/systemd/system

# .PHONY: test
# test: PREFIX := ${PWD}/install
# test: clean install
# 	scripts/test-blinky
# #	scripts/test-blinky-tape

# .PHONY: devel
# devel: PREFIX := ${PWD}/install
# devel: clean install
# 	blinky

# .PHONY: update-%
# update-%:
# 	curl "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py" -o python/$*.py
