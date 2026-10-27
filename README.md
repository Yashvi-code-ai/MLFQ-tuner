# MLFQ Tuner — Multilevel Feedback Queue Scheduler

Dependency-free Python simulation of an MLFQ CPU scheduler with configurable queues, Round Robin quanta, arrivals, preemption, demotion, priority boosts, idle periods, timeline, and metrics.

## Run

Requires Python 3.9+; no third-party packages.

```bash
python example.py
python -m unittest discover -s tests -v
```

## Use from another module

```python
from mlfq import MLFQScheduler, Process

workload = [
    Process("P1", arrival_time=0, burst_time=10),
    Process("P2", arrival_time=1, burst_time=4),
    Process("P3", arrival_time=2, burst_time=6),
]
scheduler = MLFQScheduler(quanta=[2, 4, 8], boost_interval=20)
results = scheduler.run(workload)
print(results["timeline"])
print(results["metrics"]["average_waiting_time"])
```

`quanta` also configures the number of queues. Examples: `[1, 2, 4]`, `[2, 4, 8]`, `[4, 8, 16]`. Q0 is the highest priority. Set `boost_interval=None` to disable boosts. Use `scheduler.configure(quanta=[4, 8, 16], boost_interval=30)` between runs. Input workloads are cloned, so the same workload can be safely reused with another configuration.

## Files

- `mlfq/scheduler.py`: Process, TimelineSegment, MLFQScheduler and console formatter.
- `mlfq/__init__.py`: public package exports.
- `example.py`: sample workload.
- `tests/test_scheduler.py`: unit tests.

## Algorithm and policy

1. New processes enter Q0. Simultaneous arrivals are deterministic (sorted by PID).
2. Always choose the highest-priority non-empty queue; use FIFO Round Robin inside each queue.
3. A process that consumes its full quantum without completing is demoted one level. Processes in the lowest queue remain there.
4. A higher-priority arrival preempts a lower-queue process immediately. The interrupted process retains its remaining burst and unused quantum.
5. At each boost interval, all ready processes are promoted to Q0 with a fresh Q0 quantum. A running lower-queue process is promoted at the boundary and requeued behind already-promoted ready processes. Boosts mitigate starvation.
6. If all queues are empty, advance time to the next arrival and record the idle interval.

This is a single-CPU teaching simulation; it does not model context-switch overhead or I/O blocking. Boost events are measured from time zero and are recorded during idle time as well.

## Output

`run()` returns a dictionary with:

- `timeline`: ordered segments with `pid`, `queue_level`, `queue_name`, `start_time`, `end_time`, and `duration` (ready for Gantt charts).
- `processes`: final per-process state and metrics.
- `idle_periods`: idle intervals; `boost_events`: boost timestamps.
- `metrics` and top-level aliases: average waiting, turnaround and response times; CPU utilization; throughput; total simulation, busy and idle time; process count.

Formulas: turnaround = completion − arrival; waiting = turnaround − burst; response = first start − arrival. CPU utilization = busy time / total simulation time × 100. Throughput = completed processes / total simulation time. Empty workloads return zero-valued metrics.

## Validation

PIDs must be unique non-empty strings or integers; arrival times must be non-negative; burst times, queue quanta, and enabled boost intervals must be positive finite numbers. Invalid workload item types and duplicate PIDs are rejected. Time values may be integers or floats.
