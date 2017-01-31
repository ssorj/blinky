# Blinky

Blinky collects and displays the status of CI jobs.

## Model

 - A *Component* is a piece of end-user functionality.

 - An *Environment* is a context for running a Component, such as an
   OS or language runtime.

 - An *Agent* represents a server or service that runs Jobs.  It comes
   in various types, JenkinsAgent, TravisAgent, AppveyorAgent.

 - A *Job* is a channel for repeatedly executing a test of a
   particular component in a particular Environment.  Like an Agent, a
   Job has types, JenkinsJob, TravisJob, AppveyorJob.

 - Jobs are organized into named *Groups*.  These are used for
   presentation.

 - Execution of a Job produces a *JobResult*.  A JobResult records
   whether the Job completed successfully or failed.  A Job keeps
   track of its current and previous JobResults.

See an [example configuration](https://github.com/ssorj/blinky/blob/master/misc/qpid.py).

## Dependencies

    pyserial    python3-pyserial
    tornado     python3-tornado
    requests    python3-requests

<!-- # 2. sudo usermod -G wheel,dialout jross -->
