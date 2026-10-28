import os
import tempfile
import unittest

import matplotlib
matplotlib.use("Agg")

from mlfq import MLFQScheduler, Process

from visualization import (
    create_gantt_chart,
    create_process_metric_graphs,
    create_overall_metrics_graph,
)


class TestMLFQVisualization(unittest.TestCase):

    def setUp(self):
        """Create a sample workload and run the scheduler."""

        self.workload = [
            Process("P1", arrival_time=0, burst_time=5),
            Process("P2", arrival_time=1, burst_time=3),
            Process("P3", arrival_time=2, burst_time=4),
        ]

        scheduler = MLFQScheduler(quanta=[2, 4, 8])
        self.result = scheduler.run(self.workload)

        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        """Remove temporary files after each test."""

        self.temp_dir.cleanup()

    def test_gantt_chart_is_created(self):
        """Check that the Gantt chart image is generated."""

        create_gantt_chart(self.result, self.temp_dir.name)

        path = os.path.join(
            self.temp_dir.name,
            "gantt_chart.png"
        )

        self.assertTrue(os.path.isfile(path))
        self.assertGreater(os.path.getsize(path), 0)

    def test_process_metric_graphs_are_created(self):
        """Check waiting, turnaround and response time graphs."""

        create_process_metric_graphs(
            self.result,
            self.temp_dir.name
        )

        filenames = [
            "waiting_time.png",
            "turnaround_time.png",
            "response_time.png",
        ]

        for filename in filenames:
            with self.subTest(filename=filename):
                path = os.path.join(
                    self.temp_dir.name,
                    filename
                )

                self.assertTrue(os.path.isfile(path))
                self.assertGreater(os.path.getsize(path), 0)

    def test_overall_metrics_graph_is_created(self):
        """Check that the overall performance graph is generated."""

        create_overall_metrics_graph(
            self.result,
            self.temp_dir.name
        )

        path = os.path.join(
            self.temp_dir.name,
            "overall_metrics.png"
        )

        self.assertTrue(os.path.isfile(path))
        self.assertGreater(os.path.getsize(path), 0)

    def test_scheduler_metrics_are_valid(self):
        """Validate the calculated scheduling metrics."""

        metrics = self.result["metrics"]

        self.assertGreaterEqual(
            metrics["average_waiting_time"], 0
        )

        self.assertGreaterEqual(
            metrics["average_turnaround_time"], 0
        )

        self.assertGreaterEqual(
            metrics["average_response_time"], 0
        )

        self.assertGreaterEqual(
            metrics["cpu_utilization"], 0
        )

        self.assertLessEqual(
            metrics["cpu_utilization"], 100
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

