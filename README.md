# Blinky

Blinky collects and displays the status of CI jobs.

## Overview

A *component* is a piece of end-user functionality.

An *environment* is a context for running a component, such as an OS
or language runtime.

An *agent* represents a server or service that runs jobs.  It comes in
various types: `JenkinsAgent`, `TravisAgent`, `AppVeyorAgent`, or
`GitHubAgent`.

A *job* is a channel for repeatedly executing a test of a particular
component in a particular environment.  Like an agent, a job has
types: `JenkinsJob`, `TravisJob`, `AppVeyorJob`, or `GitHubJob`.

Jobs are organized into named *groups*.  These are used for
presentation.

Execution of a job produces a *job result*.  It records whether the
job completed successfully or failed.

A job keeps track of its current and previous results.  A job blinks
if it is newly failing, meaning its current result is a failure and
its previous is a success.

See an [example configuration](https://github.com/ssorj/blinky/blob/master/misc/config.py).

## Installation

### Dependencies

| Name                  | Fedora package
| --------------------- | ---
| Python 3              | python3
| PySerial              | python3-pyserial
| Requests              | python3-requests
| Tornado               | python3-tornado

### Using Fedora packages

    $ sudo dnf enable jross/ssorj
    $ sudo dnf install blinky

If you don't have `dnf`, use the repo files at
<https://copr.fedorainfracloud.org/coprs/jross/ssorj/>.

### Installing from source

By default, installs from source go to `/usr/local`.  Make sure
`/usr/local/bin` is in your path.

    $ cd blinky/
    $ make install

## Development

To setup paths in your development environment, source the `devel.sh`
script from the project directory.

    $ cd blinky/
    $ source devel.sh

The `devel` make target creates a local installation in your checkout
and runs a sanity test.

    $ make devel

### Project layout

    devel.sh              # Sets up your project environment for development
    Makefile              # Defines the build and test targets
    bin/                  # Command-line tools
    files/                # Web server files
    python/               # Python library code
    scripts/              # Scripts called by Makefile rules
    build/                # The default build location
    install/              # The development-mode install location

### Make targets

In the development environment, most things are accomplished by
running make targets.  These are the important ones:

    $ make build         # Builds the code
    $ make install       # Installs the code
    $ make clean         # Removes build/ and install/
    $ make devel         # Builds, installs in the checkout, tests sanity
    $ make test          # Runs the test suite

<!-- # 2. sudo usermod -G wheel,dialout jross -->
