from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import isfinite
from typing import Deque, Dict, Iterable, List, Optional, Sequence, Union

Number = Union[int, float]


def _valid_time(value: object, name: str, positive: bool = False) -> Number:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < 0 or (positive and value <= 0):
        raise ValueError(f"{name} must be {'greater than zero' if positive else 'non-negative'}")
    return value


@dataclass
class Process:
    """Process workload item and its metrics; scheduler runs work on a clone."""
    pid: Union[str, int]
    arrival_time: Number
    burst_time: Number
    remaining_burst_time: Optional[Number] = None
    current_queue_level: int = 0
    start_time: Optional[Number] = None
    completion_time: Optional[Number] = None
    turnaround_time: Optional[Number] = None
    waiting_time: Optional[Number] = None
    response_time: Optional[Number] = None
    _remaining_quantum: Optional[Number] = field(default=None, repr=False, compare=False)
    _ready_since: Optional[Number] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.pid, bool) or not isinstance(self.pid, (str, int)) or not str(self.pid):
            raise ValueError("pid must be a non-empty string or integer")
        self.arrival_time = _valid_time(self.arrival_time, "arrival_time")
        self.burst_time = _valid_time(self.burst_time, "burst_time", positive=True)
        if self.remaining_burst_time is None:
            self.remaining_burst_time = self.burst_time
        else:
            self.remaining_burst_time = _valid_time(self.remaining_burst_time, "remaining_burst_time", positive=True)
            if self.remaining_burst_time > self.burst_time:
                raise ValueError("remaining_burst_time cannot exceed burst_time")

    def clone_for_run(self) -> "Process":
        return Process(self.pid, self.arrival_time, self.burst_time)

    def to_dict(self) -> Dict[str, object]:
        return {"pid": self.pid, "arrival_time": self.arrival_time, "burst_time": self.burst_time,
                "remaining_burst_time": self.remaining_burst_time, "current_queue_level": self.current_queue_level,
                "start_time": self.start_time, "completion_time": self.completion_time,
                "turnaround_time": self.turnaround_time, "waiting_time": self.waiting_time,
                "response_time": self.response_time}


@dataclass(frozen=True)
class TimelineSegment:
    """A contiguous CPU execution interval."""
    pid: Union[str, int]
    queue_level: int
    start_time: Number
    end_time: Number

    @property
    def duration(self) -> Number:
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, object]:
        return {"pid": self.pid, "queue_level": self.queue_level, "queue_name": f"Q{self.queue_level}",
                "start_time": self.start_time, "end_time": self.end_time, "duration": self.duration}


class MLFQScheduler:
    """Single CPU MLFQ simulator with Round Robin, preemption, and priority boosts.

    quanta selects the queue count and gives each queue its own time quantum.
    Q0 is highest priority. Set boost_interval=None to disable priority boosts.
    Higher-priority arrivals preempt lower-queue execution; the interrupted job
    preserves its remaining burst and unused quantum. Boosting moves ready jobs
    to Q0 and resets their quantum, mitigating starvation.
    """

    def __init__(self, quanta: Sequence[Number] = (2, 4, 8),
                 boost_interval: Optional[Number] = None) -> None:
        self.quanta = self._validate_quanta(quanta)
        self.boost_interval = self._validate_boost(boost_interval)
        self.queue_count = len(self.quanta)
        self.queues: List[Deque[Process]] = [deque() for _ in self.quanta]
        self.timeline: List[TimelineSegment] = []
        self.idle_periods: List[Dict[str, Number]] = []
        self.boost_events: List[Number] = []
        self._clock: Number = 0

    @staticmethod
    def _validate_quanta(quanta: Sequence[Number]) -> List[Number]:
        if isinstance(quanta, (str, bytes)) or not isinstance(quanta, Sequence) or not quanta:
            raise ValueError("quanta must be a non-empty sequence of positive numbers")
        return [_valid_time(q, f"quanta[{i}]", True) for i, q in enumerate(quanta)]

    @staticmethod
    def _validate_boost(interval: Optional[Number]) -> Optional[Number]:
        return None if interval is None else _valid_time(interval, "boost_interval", True)

    def configure(self, *, quanta: Optional[Sequence[Number]] = None,
                  boost_interval: object = ...) -> None:
        """Update settings for subsequent simulations."""
        if quanta is not None:
            self.quanta = self._validate_quanta(quanta)
            self.queue_count = len(self.quanta)
        if boost_interval is not ...:
            self.boost_interval = self._validate_boost(boost_interval)  # type: ignore[arg-type]

    def run(self, processes: Iterable[Process]) -> Dict[str, object]:
        """Run one fresh simulation and return timeline, process rows and metrics."""
        try:
            original = list(processes)
        except TypeError as exc:
            raise ValueError("processes must be an iterable of Process objects") from exc
        if any(not isinstance(p, Process) for p in original):
            raise ValueError("every workload item must be a Process")
        pids = [str(p.pid) for p in original]
        if len(pids) != len(set(pids)):
            raise ValueError("process IDs must be unique")
        for p in original:
            _valid_time(p.arrival_time, f"arrival_time for {p.pid}")
            _valid_time(p.burst_time, f"burst_time for {p.pid}", True)

        jobs = [p.clone_for_run() for p in original]
        jobs.sort(key=lambda p: (p.arrival_time, str(p.pid)))
        self.queues = [deque() for _ in self.quanta]
        self.timeline, self.idle_periods, self.boost_events = [], [], []
        self._clock = 0
        if not jobs:
            return self._result(jobs)

        next_arrival, completed = 0, 0
        next_boost: Optional[Number] = self.boost_interval
        running: Optional[Process] = None

        def admit(now: Number) -> None:
            nonlocal next_arrival
            while next_arrival < len(jobs) and jobs[next_arrival].arrival_time <= now:
                p = jobs[next_arrival]
                p.current_queue_level = 0
                p._remaining_quantum = self.quanta[0]
                p._ready_since = p.arrival_time
                self.queues[0].append(p)
                next_arrival += 1

        def boost(now: Number) -> None:
            nonlocal next_boost
            ready: List[Process] = []
            for q in self.queues:
                while q:
                    ready.append(q.popleft())
            for p in ready:
                p.current_queue_level = 0
                p._remaining_quantum = self.quanta[0]
                self.queues[0].append(p)
            self.boost_events.append(now)
            next_boost = now + self.boost_interval if self.boost_interval is not None else None

        while completed < len(jobs):
            admit(self._clock)
            if next_boost is not None and next_boost <= self._clock:
                boost(self._clock)

            if running is not None and any(self.queues[i] for i in range(running.current_queue_level)):
                running._ready_since = self._clock
                self.queues[running.current_queue_level].appendleft(running)
                running = None

            if running is None:
                level = next((i for i, q in enumerate(self.queues) if q), None)
                if level is None:
                    if next_arrival >= len(jobs):
                        raise RuntimeError("scheduler reached a deadlock with unfinished processes")
                    event = jobs[next_arrival].arrival_time
                    if next_boost is not None:
                        event = min(event, next_boost)
                    if event > self._clock:
                        if self.idle_periods and self.idle_periods[-1]["end_time"] == self._clock:
                            self.idle_periods[-1]["end_time"] = event
                        else:
                            self.idle_periods.append({"start_time": self._clock, "end_time": event})
                        self._clock = event
                    if next_boost is not None and next_boost == self._clock:
                        boost(self._clock)
                    continue
                running = self.queues[level].popleft()
                running.current_queue_level = level
                running._ready_since = None
                if running._remaining_quantum is None or running._remaining_quantum <= 0:
                    running._remaining_quantum = self.quanta[level]

            level = running.current_queue_level
            quantum = running._remaining_quantum or self.quanta[level]
            end = self._clock + min(running.remaining_burst_time or 0, quantum)
            if next_arrival < len(jobs):
                end = min(end, jobs[next_arrival].arrival_time)
            if next_boost is not None:
                end = min(end, next_boost)
            if end <= self._clock:
                admit(self._clock)
                if next_boost is not None and next_boost <= self._clock:
                    boost(self._clock)
                continue

            start = self._clock
            if running.start_time is None:
                running.start_time = start
                running.response_time = start - running.arrival_time
            self.timeline.append(TimelineSegment(running.pid, level, start, end))
            elapsed = end - start
            running.remaining_burst_time = (running.remaining_burst_time or 0) - elapsed
            running._remaining_quantum = (running._remaining_quantum or 0) - elapsed
            self._clock = end
            admit(self._clock)
            boost_now = next_boost is not None and next_boost == self._clock
            if boost_now:
                boost(self._clock)

            if running.remaining_burst_time == 0:
                running.completion_time = self._clock
                running.turnaround_time = self._clock - running.arrival_time
                running.waiting_time = running.turnaround_time - running.burst_time
                completed += 1
                running = None
                continue
            if boost_now and level > 0:
                running.current_queue_level = 0
                running._remaining_quantum = self.quanta[0]
                running._ready_since = self._clock
                self.queues[0].append(running)
                running = None
                continue
            if any(self.queues[i] for i in range(level)):
                running._ready_since = self._clock
                self.queues[level].appendleft(running)
                running = None
                continue
            if running._remaining_quantum == 0:
                lower = min(level + 1, self.queue_count - 1)
                running.current_queue_level = lower
                running._remaining_quantum = self.quanta[lower]
                running._ready_since = self._clock
                self.queues[lower].append(running)
                running = None

        return self._result(jobs)

    def _result(self, jobs: Sequence[Process]) -> Dict[str, object]:
        n, total = len(jobs), self._clock
        busy = sum(segment.duration for segment in self.timeline)
        waits = [p.waiting_time for p in jobs if p.waiting_time is not None]
        turns = [p.turnaround_time for p in jobs if p.turnaround_time is not None]
        responses = [p.response_time for p in jobs if p.response_time is not None]
        metrics: Dict[str, object] = {
            "average_waiting_time": sum(waits) / n if n else 0,
            "average_turnaround_time": sum(turns) / n if n else 0,
            "average_response_time": sum(responses) / n if n else 0,
            "cpu_utilization": busy / total * 100 if total else 0,
            "throughput": n / total if total else 0,
            "total_simulation_time": total,
            "total_busy_time": busy,
            "total_idle_time": total - busy,
            "process_count": n,
        }
        return {"timeline": [s.to_dict() for s in self.timeline],
                "idle_periods": [dict(p) for p in self.idle_periods],
                "boost_events": list(self.boost_events),
                "processes": [p.to_dict() for p in jobs], "metrics": metrics, **metrics}


def format_result(result: Dict[str, object]) -> str:
    """Format results for a console demo."""
    lines = ["MLFQ Scheduler Results", "=" * 22, "", "Execution timeline:"]
    timeline = result["timeline"]
    if not timeline:
        lines.append("  (no execution)")
    else:
        for s in timeline:  # type: ignore[union-attr]
            lines.append(f"  {s['start_time']:>5} - {s['end_time']:<5} {s['pid']} ({s['queue_name']}, {s['duration']} units)")
    lines += ["", "Per-process metrics:", "  PID  Arrival  Burst  Complete  Turnaround  Waiting  Response"]
    for p in result["processes"]:  # type: ignore[union-attr]
        lines.append(f"  {str(p['pid']):<4} {str(p['arrival_time']):<7} {str(p['burst_time']):<6} "
                     f"{str(p['completion_time']):<9} {str(p['turnaround_time']):<10} "
                     f"{str(p['waiting_time']):<7} {p['response_time']}")
    metrics = result["metrics"]  # type: ignore[assignment]
    lines += ["", "Scheduler metrics:"]
    labels = [("average_waiting_time", "Average waiting time"), ("average_turnaround_time", "Average turnaround time"),
              ("average_response_time", "Average response time"), ("cpu_utilization", "CPU utilization (%)"),
              ("throughput", "Throughput (processes / time unit)"), ("total_simulation_time", "Total simulation time")]
    for key, label in labels:
        lines.append(f"  {label}: {metrics[key]:.2f}")
    if result["idle_periods"]:
        lines.append(f"  Idle periods: {result['idle_periods']}")
    if result["boost_events"]:
        lines.append(f"  Priority boosts: {result['boost_events']}")
    return "\n".join(lines)
