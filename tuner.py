

"""
MLFQ Tuner & Performance Analysis
Uses the team's actual MLFQ scheduler to compare configurations.
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

from mlfq.scheduler import MLFQScheduler, Process


# Same workload for every configuration: fair comparison
WORKLOAD = [
    (1, 0, 10),
    (2, 1, 5),
    (3, 2, 8),
    (4, 3, 2),
    (5, 5, 6),
    (6, 7, 3),
    (7, 9, 12),
    (8, 12, 4),
]

# Different queue time quanta to test
QUANTA_OPTIONS = [
    (1, 2, 4),
    (2, 4, 8),
    (3, 6, 12),
]

# Test disabled boosts and two boost intervals
BOOST_OPTIONS = [None, 10, 20]

OUTPUT_DIR = Path("tuner_results")


def create_workload():
    """Create a fresh set of processes for each experiment."""
    return [
        Process(pid=pid, arrival_time=arrival, burst_time=burst)
        for pid, arrival, burst in WORKLOAD
    ]


def run_experiment(quanta, boost_interval):
    """Run the real scheduler and collect its performance metrics."""
    scheduler = MLFQScheduler(
        quanta=quanta,
        boost_interval=boost_interval,
    )

    result = scheduler.run(create_workload())
    metrics = result["metrics"]

    return {
        "quanta": str(tuple(quanta)),
        "boost_interval": (
            "Disabled" if boost_interval is None else boost_interval
        ),
        "average_waiting_time": metrics["average_waiting_time"],
        "average_turnaround_time": metrics["average_turnaround_time"],
        "average_response_time": metrics["average_response_time"],
        "cpu_utilization": metrics["cpu_utilization"],
        "throughput": metrics["throughput"],
        "total_simulation_time": metrics["total_simulation_time"],
    }


def save_csv(results):
    """Save all experiment results to a CSV file."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_path = OUTPUT_DIR / "comparison_results.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to: {csv_path}")


def create_graphs(results):
    """Generate comparison charts for the tested configurations."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    labels = [
        f"{row['quanta']}\nBoost={row['boost_interval']}"
        for row in results
    ]

    metrics_to_plot = [
        ("average_waiting_time", "Average Waiting Time"),
        ("average_turnaround_time", "Average Turnaround Time"),
        ("average_response_time", "Average Response Time"),
        ("cpu_utilization", "CPU Utilization (%)"),
        ("throughput", "Throughput"),
    ]

    for metric, title in metrics_to_plot:
        values = [float(row[metric]) for row in results]

        plt.figure(figsize=(12, 6))
        plt.bar(range(len(labels)), values)
        plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
        plt.ylabel(title)
        plt.title(f"MLFQ Configuration Comparison: {title}")
        plt.tight_layout()

        filename = OUTPUT_DIR / f"{metric}.png"
        plt.savefig(filename, dpi=150)
        plt.close()

        print(f"Graph saved: {filename}")


def main():
    results = []

    print("MLFQ Tuner & Performance Analysis")
    print("=" * 40)

    for quanta in QUANTA_OPTIONS:
        for boost_interval in BOOST_OPTIONS:
            row = run_experiment(quanta, boost_interval)
            results.append(row)

            print(
                f"Quanta={quanta}, Boost={boost_interval}, "
                f"Waiting={row['average_waiting_time']:.2f}, "
                f"Response={row['average_response_time']:.2f}, "
                f"Turnaround={row['average_turnaround_time']:.2f}, "
                f"CPU={row['cpu_utilization']:.2f}%, "
                f"Throughput={row['throughput']:.4f}"
            )

    # Lowest average waiting time is the selected criterion.
    best = min(results, key=lambda row: row["average_waiting_time"])

    print("\nBest configuration by average waiting time:")
    print(f"  Queue quanta: {best['quanta']}")
    print(f"  Boost interval: {best['boost_interval']}")
    print(f"  Average waiting time: {best['average_waiting_time']:.2f}")

    save_csv(results)
    create_graphs(results)

    print("\nAll experiments completed.")


if __name__ == "__main__":
    main()
