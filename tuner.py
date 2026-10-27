
"""
MLFQ Tuner & Performance Analysis
Tests multiple workloads using the team's actual scheduler.
"""

import csv
from pathlib import Path
import matplotlib.pyplot as plt

from mlfq.scheduler import MLFQScheduler, Process

OUTPUT_DIR = Path("tuner_results")

# Each process: (PID, arrival time, CPU burst)
WORKLOADS = {
    "Interactive": [
        (1, 0, 2), (2, 1, 1), (3, 2, 3), (4, 4, 1),
        (5, 5, 2), (6, 7, 1), (7, 8, 3),
    ],
    "CPU Intensive": [
        (1, 0, 20), (2, 0, 18), (3, 1, 25),
        (4, 2, 15), (5, 3, 22), (6, 4, 17),
    ],
    "Long Gaps": [
        (1, 0, 5), (2, 15, 3), (3, 35, 8),
        (4, 60, 2), (5, 90, 6),
    ],
}

QUANTA_OPTIONS = [(1, 2, 4), (2, 4, 8), (3, 6, 12)]
BOOST_OPTIONS = [None, 10, 20]

METRICS = [
    "average_waiting_time",
    "average_turnaround_time",
    "average_response_time",
    "cpu_utilization",
    "throughput",
]


def make_processes(workload):
    """Create a fresh workload for every scheduler run."""
    return [
        Process(pid=pid, arrival_time=arrival, burst_time=burst)
        for pid, arrival, burst in workload
    ]


def run_experiment(workload_name, workload, quanta, boost):
    scheduler = MLFQScheduler(quanta=quanta, boost_interval=boost)
    result = scheduler.run(make_processes(workload))

    row = {
        "workload": workload_name,
        "quanta": str(quanta),
        "boost_interval": "Disabled" if boost is None else boost,
    }
    row.update(result["metrics"])
    return row


def save_results(rows):
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / "multi_workload_results.csv"

    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV saved: {path}")


def create_graphs(rows):
    OUTPUT_DIR.mkdir(exist_ok=True)

    # One graph per metric, with configuration comparisons
    for metric in METRICS:
        plt.figure(figsize=(12, 6))

        for workload_name in WORKLOADS:
            selected = [
                row for row in rows
                if row["workload"] == workload_name
            ]
            labels = [
                f"{row['quanta']}\nB={row['boost_interval']}"
                for row in selected
            ]
            values = [float(row[metric]) for row in selected]

            # Plot each workload separately to keep comparisons readable.
            plt.plot(
                range(len(values)), values,
                marker="o", label=workload_name
            )

        plt.title(f"MLFQ Configuration Comparison: {metric}")
        plt.xlabel("Configuration index (same order for each workload)")
        plt.ylabel(metric.replace("_", " ").title())
        plt.legend()
        plt.tight_layout()

        path = OUTPUT_DIR / f"multi_{metric}.png"
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"Graph saved: {path}")


def main():
    rows = []

    for workload_name, workload in WORKLOADS.items():
        print(f"\n=== {workload_name} workload ===")

        for quanta in QUANTA_OPTIONS:
            for boost in BOOST_OPTIONS:
                row = run_experiment(
                    workload_name, workload, quanta, boost
                )
                rows.append(row)

                print(
                    f"Quanta={quanta}, Boost={row['boost_interval']}, "
                    f"Waiting={row['average_waiting_time']:.2f}, "
                    f"Turnaround={row['average_turnaround_time']:.2f}, "
                    f"Response={row['average_response_time']:.2f}, "
                    f"CPU={row['cpu_utilization']:.2f}%, "
                    f"Throughput={row['throughput']:.4f}"
                )

    print(f"\nCompleted {len(rows)} experiments.")

    # Best configuration per workload, using waiting time as the criterion.
    print("\nBest configuration by workload (lowest average waiting time):")
    for workload_name in WORKLOADS:
        candidates = [r for r in rows if r["workload"] == workload_name]
        best = min(candidates, key=lambda r: r["average_waiting_time"])
        print(
            f"{workload_name}: quanta={best['quanta']}, "
            f"boost={best['boost_interval']}, "
            f"waiting={best['average_waiting_time']:.2f}"
        )

    save_results(rows)
    create_graphs(rows)
    print("\nAll multi-workload experiments completed.")


if __name__ == "__main__":
    main()
