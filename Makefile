# 1. dnf install python3-pyserial python3-requests python3-tornado
# 2. sudo usermod -G wheel,dialout jross

DESTDIR := ""
PREFIX := /usr/local
home = ${PREFIX}/share/blinky

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
	mkdir -p build/bin
	mkdir -p build/misc
	scripts/configure-file bin/blinky.in build/bin/blinky blinky_home ${home}
	scripts/configure-file bin/blinky-tape.in build/bin/blinky-tape blinky_home ${home}
	scripts/configure-file misc/blinky.service.in build/misc/blinky.service PREFIX ${PREFIX}
	scripts/configure-file misc/blinky-tape.service.in build/misc/blinky-tape.service PREFIX ${PREFIX}

.PHONY: install
install: build
	scripts/install-files python ${DESTDIR}${home}/python \*.py
	scripts/install-files files ${DESTDIR}${home}/files \*
	install -d ${DESTDIR}${PREFIX}/bin
	install -d ${DESTDIR}${PREFIX}/lib/systemd/system
	install -m 755 build/bin/blinky ${DESTDIR}${PREFIX}/bin/blinky
	install -m 755 build/bin/blinky-tape ${DESTDIR}${PREFIX}/bin/blinky-tape
	install -m 644 build/misc/blinky.service ${DESTDIR}${PREFIX}/lib/systemd/system/blinky.service
	install -m 644 build/misc/blinky-tape.service ${DESTDIR}${PREFIX}/lib/systemd/system/blinky-tape.service

.PHONY: test
test: PREFIX := ${PWD}/install
test: clean install
	${PREFIX}/bin/blinky --init-only

.PHONY: devel
devel: PREFIX := ${PWD}/install
devel: clean install
	${PREFIX}/bin/blinky

.PHONY: update-%
update-%:
	curl "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py" -o python/$*.py
