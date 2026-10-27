# MLFQ Tuner — Multilevel Feedback Queue Scheduler

Dependency-free Python simulation of an MLFQ CPU scheduler with configurable queues, Round Robin quanta, arrivals, preemption, demotion, priority boosts, idle periods, execution timeline, and process/scheduler metrics.

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

`quanta` also configures the number of queues. Examples: `[1, 2, 4]`, `[2, 4, 8]`, `[4, 8, 16]`. Q0 is highest priority. Set `boost_interval=None` to disable boosts. Reconfigure with `scheduler.configure(quanta=[4, 8, 16], boost_interval=30)`. Workloads are cloned on each run and can be reused unchanged.

## Project files

- `mlfq/scheduler.py`: `Process`, `TimelineSegment`, `MLFQScheduler`, and console formatter.
- `mlfq/__init__.py`: public exports.
- `example.py`: sample workload.
- `tests/test_scheduler.py`: tests for scheduling behavior and edge cases.

## Algorithm

1. New arrivals enter Q0. Simultaneous arrivals are deterministic (sorted by PID).
2. The scheduler chooses the highest-priority non-empty queue and uses FIFO Round Robin within the queue.
3. A process that consumes its full quantum without finishing is demoted by one level. Processes in the lowest queue stay there.
4. An arrival in a higher-priority queue preempts lower-queue execution immediately. The interrupted process retains its remaining burst and unused quantum.
5. At each boost interval, ready processes are promoted to Q0 with a fresh Q0 quantum. A running lower-level process is promoted at the boundary and requeued behind other promoted jobs. This reduces starvation.
6. When no process is ready, the clock advances to the next arrival and the idle interval is recorded.

This is a single-CPU teaching simulation without context-switch overhead or I/O blocking. Boost events are measured from time zero and recorded during idle periods too.

## Results and metrics

`run()` returns a dictionary:

- `timeline`: ordered execution segments with PID, queue level/name, start, end, and duration; ready for Gantt chart visualization.
- `processes`: final process state and per-process metrics.
- `idle_periods` and `boost_events`: recorded scheduler events.
- `metrics` plus top-level aliases: average waiting, turnaround and response time; CPU utilization; throughput; total simulation, busy and idle time; process count.

Formulas: turnaround = completion − arrival; waiting = turnaround − burst; response = first start − arrival. CPU utilization = busy time / total simulation time × 100. Throughput = completed processes / total simulation time. Empty workloads return zero-valued aggregate metrics.

## Validation

PIDs must be unique non-empty strings or integers, arrival times must be non-negative, and burst times, queue quanta, and enabled boost intervals must be positive finite numbers. Invalid process item types and duplicate PIDs are rejected. Time values can be integers or floats.
