"""Run the project's sample workload."""

from mlfq import MLFQScheduler, Process, format_result


def main() -> None:
    workload = [
        Process("P1", arrival_time=0, burst_time=10),
        Process("P2", arrival_time=1, burst_time=4),
        Process("P3", arrival_time=2, burst_time=6),
    ]
    scheduler = MLFQScheduler(quanta=[2, 4, 8], boost_interval=20)
    print(format_result(scheduler.run(workload)))


if __name__ == "__main__":
    main()
