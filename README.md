# Blinky

Blinky collects and displays the status of CI jobs.

## Model

 - An `Agent` represents a server or service that runs CI jobs.  It
   comes in various types, `JenkinsAgent`, `TravisAgent`,
   `AppveyorAgent`.

 - A `Test` is a particular suite of test operations.  It might
   correspond to `make check` for your project.  A `Test` belongs to a
   named `TestGroup`.

 - An `Environment` describes a context for test execution, such as an
   OS or language runtime.

 - A `Job` is a channel for repeatedly executing a `Test` in a
   particular `Environment`.  A `Job` carries test results.  Like an
   `Agent`, a `Job` has types, `JenkinsJob`, `TravisJob`,
   `AppveyorJob`.
