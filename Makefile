VERSION := $(shell cat VERSION.txt)

DESTDIR := ""
PREFIX := /usr/local
BLINKY_HOME = ${PREFIX}/share/blinky

export PATH := install/bin:${PATH}
export PYTHONPATH := python:${PYTHONPATH}

.PHONY: default
default: devel

.PHONY: help
help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "clean          Clean up the source tree"
	@echo "devel          Build, install, and run in this development session"

.PHONY: clean
clean:
	find python -type f -name \*.pyc -delete
	find python -type d -name __pycache__ -delete
	rm -rf build
	rm -rf install

.PHONY: build
build:
	scripts/configure-file -a blinky_home=${BLINKY_HOME} bin/blinky.in build/bin/blinky
	scripts/configure-file -a blinky_home=${BLINKY_HOME} bin/blinky-tape.in build/bin/blinky-tape
	scripts/configure-file -a PREFIX=${PREFIX} misc/blinky.service.in build/misc/blinky.service
	scripts/configure-file -a PREFIX=${PREFIX} misc/blinky-tape.service.in build/misc/blinky-tape.service

.PHONY: install
install: build
	scripts/install-files -n \*.py python ${DESTDIR}${BLINKY_HOME}/python
	scripts/install-files files ${DESTDIR}${BLINKY_HOME}/files
	scripts/install-files build/bin ${DESTDIR}${PREFIX}/bin
	scripts/install-files -n \*.service build/misc ${DESTDIR}${PREFIX}/lib/systemd/system

.PHONY: test
test: PREFIX := ${PWD}/install
test: clean install
	scripts/test-blinky
	scripts/test-blinky-tape

.PHONY: devel
devel: PREFIX := ${PWD}/install
devel: clean install

.PHONY: update-%
update-%:
	curl "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py" -o python/$*.py
