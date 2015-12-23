# Blinky

Blinky collects and displays the status of CI jobs.

## Model

 - A `Component` is a piece of end-user functionality.

 - An `Environment` is a context for running a `Component`, such as an
   OS or language runtime.

 - A `Test` is a particular suite of test operations.  It might
   correspond to `make check` for your project.  A `Test` belongs to a
   named `TestGroup`.  A `Test` has a target `Component`.

 - An `Agent` represents a server or service that runs `Job`s.  It
   comes in various types, `JenkinsAgent`, `TravisAgent`,
   `AppveyorAgent`.

 - A `Job` is a channel for repeatedly executing a `Test` in a
   particular `Environment`.  A `Job` carries test results.  Like an
   `Agent`, a `Job` has types, `JenkinsJob`, `TravisJob`,
   `AppveyorJob`.

See an [example configuration](https://github.com/ssorj/blinky/blob/master/misc/qpid.py).
