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
types: `CircleCiJob`, `JenkinsJob`, `TravisCiJob`, `AppVeyorJob`, or
`GitHubJob`.

Jobs are organized into named *groups*.  These are used for
presentation.

The execution of a job is a *job run*.  Once complete, the job run
indicates whether it passed or failed.

A job keeps track of its current and previous results.  A job blinks
if it is newly failing, meaning its current result is a failure and
its previous is a success.

See an [example configuration](https://github.com/ssorj/blinky/blob/master/misc/config.py).

## Installation

### Dependencies

    sudo dnf install python3-httpx python3-uvicorn

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
