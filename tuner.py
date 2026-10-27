
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

QUANTA_OPTIONS = [
    (1, 2, 4),
    (2, 4, 8),
    (3, 6, 12),
]

BOOST_OPTIONS = [None, 10, 20]

METRICS = [
    "average_waiting_time",
    "average_turnaround_time",
    "average_response_time",
    "cpu_utilization",
    "throughput",
]


def make_processes(workload):
    """Create fresh processes for every scheduler run."""
    return [
        Process(
            pid=pid,
            arrival_time=arrival,
            burst_time=burst,
        )
        for pid, arrival, burst in workload
    ]


def run_experiment(workload_name, workload, quanta, boost):
    """Run the actual MLFQ scheduler and collect its metrics."""
    scheduler = MLFQScheduler(
        quanta=quanta,
        boost_interval=boost,
    )

    result = scheduler.run(make_processes(workload))

    row = {
        "workload": workload_name,
        "quanta": str(quanta),
        "boost_interval": "Disabled" if boost is None else boost,
    }

    row.update(result["metrics"])
    return row


def save_results(rows):
    """Save all experiment results to a CSV file."""
    if not rows:
        print("No results to save.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "multi_workload_results.csv"

    fields = list(rows[0].keys())

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV saved: {path}")


def create_graphs(rows):
    """Generate comparison graphs for every performance metric."""
    if not rows:
        print("No results available for graph generation.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for metric in METRICS:
        fig, axes = plt.subplots(
            nrows=len(WORKLOADS),
            ncols=1,
            figsize=(14, 15),
        )

        # Make axes iterable if there is only one workload.
        if len(WORKLOADS) == 1:
            axes = [axes]

        for ax, workload_name in zip(axes, WORKLOADS):
            selected = [
                row for row in rows
                if row["workload"] == workload_name
            ]

            labels = [
                f"Q={row['quanta']}\nB={row['boost_interval']}"
                for row in selected
            ]

            values = [
                float(row[metric])
                for row in selected
            ]

            positions = range(len(values))
            ax.bar(positions, values)

            # Make all-zero results visible instead of leaving a blank plot.
            if values and all(value == 0 for value in values):
                ax.text(
                    0.5,
                    0.5,
                    "All configurations: 0.00",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=12,
                )

            ax.set_xticks(list(positions))
            ax.set_xticklabels(
                labels,
                rotation=45,
                ha="right",
                fontsize=8,
            )

            ax.set_title(f"{workload_name} Workload")
            ax.set_ylabel(metric.replace("_", " ").title())
            ax.grid(axis="y", linestyle="--", alpha=0.4)

        fig.suptitle(
            "MLFQ Configuration Comparison: "
            f"{metric.replace('_', ' ').title()}",
            fontsize=14,
        )

        fig.tight_layout(rect=[0, 0, 1, 0.97])

        path = OUTPUT_DIR / f"multi_{metric}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        print(f"Graph saved: {path}")


def report_best_configurations(rows):
    """Report every configuration tied for lowest waiting time."""
    print(
        "\nBest configuration by workload "
        "(lowest average waiting time):"
    )

    for workload_name in WORKLOADS:
        candidates = [
            row for row in rows
            if row["workload"] == workload_name
        ]

        if not candidates:
            print(f"{workload_name}: No results available.")
            continue

        best_waiting_time = min(
            row["average_waiting_time"]
            for row in candidates
        )

        for best in candidates:
            if best["average_waiting_time"] == best_waiting_time:
                print(
                    f"{workload_name}: "
                    f"Quanta={best['quanta']}, "
                    f"Boost={best['boost_interval']}, "
                    f"Waiting={best['average_waiting_time']:.2f}"
                )


def main():
    rows = []

    print("MLFQ Tuner & Performance Analysis")
    print("=" * 45)

    for workload_name, workload in WORKLOADS.items():
        print(f"\n=== {workload_name} workload ===")

        for quanta in QUANTA_OPTIONS:
            for boost in BOOST_OPTIONS:
                row = run_experiment(
                    workload_name,
                    workload,
                    quanta,
                    boost,
                )

                rows.append(row)

                print(
                    f"Quanta={quanta}, "
                    f"Boost={row['boost_interval']}, "
                    f"Waiting={row['average_waiting_time']:.2f}, "
                    f"Turnaround={row['average_turnaround_time']:.2f}, "
                    f"Response={row['average_response_time']:.2f}, "
                    f"CPU={row['cpu_utilization']:.2f}%, "
                    f"Throughput={row['throughput']:.4f}"
                )

    print(f"\nCompleted {len(rows)} experiments.")

    report_best_configurations(rows)
    save_results(rows)
    create_graphs(rows)

    print("\nAll multi-workload experiments completed.")


if __name__ == "__main__":
    main()
