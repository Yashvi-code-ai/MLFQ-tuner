import os
import matplotlib.pyplot as plt

from mlfq import MLFQScheduler, Process


def create_gantt_chart(result, output_dir):
    """Create a CPU scheduling Gantt chart."""

    timeline = result["timeline"]

    if not timeline:
        print("No execution timeline available.")
        return

    fig, ax = plt.subplots(figsize=(12, 5))

    process_ids = list(dict.fromkeys(
        str(segment["pid"]) for segment in timeline
    ))

    positions = {
        pid: index for index, pid in enumerate(process_ids)
    }

    for segment in timeline:
        pid = str(segment["pid"])
        start = segment["start_time"]
        end = segment["end_time"]

        ax.barh(
            positions[pid],
            end - start,
            left=start,
            height=0.55,
            edgecolor="black"
        )

        ax.text(
            (start + end) / 2,
            positions[pid],
            f'{pid} ({segment["queue_name"]})',
            ha="center",
            va="center",
            fontsize=8
        )

    ax.set_yticks(list(positions.values()))
    ax.set_yticklabels(process_ids)
    ax.set_xlabel("Execution Time")
    ax.set_ylabel("Process")
    ax.set_title("MLFQ CPU Scheduling Gantt Chart")
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    fig.tight_layout()

    path = os.path.join(output_dir, "gantt_chart.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)

    print(f"Gantt chart saved: {path}")


def create_process_metric_graphs(result, output_dir):
    """Create process-wise performance graphs."""

    processes = result["processes"]

    if not processes:
        print("No processes available.")
        return

    pids = [str(p["pid"]) for p in processes]

    graph_settings = [
        ("waiting_time", "Waiting Time", "waiting_time.png"),
        ("turnaround_time", "Turnaround Time", "turnaround_time.png"),
        ("response_time", "Response Time", "response_time.png"),
    ]

    for key, title, filename in graph_settings:
        values = [p[key] for p in processes]

        fig, ax = plt.subplots(figsize=(8, 4))

        bars = ax.bar(pids, values, edgecolor="black")
        ax.bar_label(bars, fmt="%.2f", padding=3)

        ax.set_title(f"Process-wise {title}")
        ax.set_xlabel("Process")
        ax.set_ylabel("Time")
        ax.grid(axis="y", linestyle="--", alpha=0.4)

        fig.tight_layout()

        path = os.path.join(output_dir, filename)
        fig.savefig(path, dpi=150)
        plt.close(fig)

        print(f"{title} graph saved: {path}")


def create_overall_metrics_graph(result, output_dir):
    """Create an overall scheduler performance graph."""

    metrics = result["metrics"]

    labels = [
        "Avg Waiting",
        "Avg Turnaround",
        "Avg Response",
        "CPU Utilization (%)",
    ]

    values = [
        metrics["average_waiting_time"],
        metrics["average_turnaround_time"],
        metrics["average_response_time"],
        metrics["cpu_utilization"],
    ]

    fig, ax = plt.subplots(figsize=(9, 5))

    bars = ax.bar(labels, values, edgecolor="black")
    ax.bar_label(bars, fmt="%.2f", padding=3)

    ax.set_title("Overall MLFQ Performance")
    ax.set_ylabel("Value")
    ax.tick_params(axis="x", rotation=15)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()

    path = os.path.join(output_dir, "overall_metrics.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)

    print(f"Overall metrics graph saved: {path}")


def main():
    output_dir = "visualization_results"
    os.makedirs(output_dir, exist_ok=True)

    # Sample workload
    workload = [
        Process("P1", arrival_time=0, burst_time=10),
        Process("P2", arrival_time=1, burst_time=4),
        Process("P3", arrival_time=2, burst_time=6),
    ]

    # Use the existing MLFQ scheduler
    scheduler = MLFQScheduler(
        quanta=[2, 4, 8],
        boost_interval=20
    )

    result = scheduler.run(workload)

    print("\nMLFQ Performance Summary")
    print("-" * 35)

    metrics = result["metrics"]

    print(f"Average Waiting Time: {metrics['average_waiting_time']:.2f}")
    print(
        "Average Turnaround Time: "
        f"{metrics['average_turnaround_time']:.2f}"
    )
    print(f"Average Response Time: {metrics['average_response_time']:.2f}")
    print(f"CPU Utilization: {metrics['cpu_utilization']:.2f}%")
    print(f"Throughput: {metrics['throughput']:.4f}")

    create_gantt_chart(result, output_dir)
    create_process_metric_graphs(result, output_dir)
    create_overall_metrics_graph(result, output_dir)

    print("\nAll visualizations generated successfully!")


if __name__ == "__main__":
    main()
