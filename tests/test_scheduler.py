import unittest

from mlfq import MLFQScheduler, Process


class MLFQSchedulerTests(unittest.TestCase):
    def test_empty_workload(self):
        result = MLFQScheduler().run([])
        self.assertEqual(result["timeline"], [])
        self.assertEqual(result["total_simulation_time"], 0)
        self.assertEqual(result["cpu_utilization"], 0)
        self.assertEqual(result["throughput"], 0)

    def test_single_process_metrics(self):
        result = MLFQScheduler([2, 4, 8]).run([Process("P1", 0, 5)])
        p = result["processes"][0]
        self.assertEqual((p["completion_time"], p["turnaround_time"], p["waiting_time"], p["response_time"]), (5, 5, 0, 0))
        self.assertEqual([s["queue_level"] for s in result["timeline"]], [0, 1])

    def test_demote_through_queues_and_stay_at_lowest(self):
        result = MLFQScheduler([1, 2, 3]).run([Process("P", 0, 8)])
        self.assertEqual([s["queue_level"] for s in result["timeline"]], [0, 1, 2, 2])
        self.assertEqual(result["processes"][0]["completion_time"], 8)

    def test_round_robin_fifo(self):
        result = MLFQScheduler([2, 4, 8], boost_interval=None).run([Process("A", 0, 4), Process("B", 0, 4)])
        self.assertEqual([(s["pid"], s["start_time"], s["end_time"]) for s in result["timeline"][:2]], [("A", 0, 2), ("B", 2, 4)])

    def test_higher_priority_arrival_preempts_lower_queue(self):
        result = MLFQScheduler([2, 4, 8], boost_interval=None).run([Process("A", 0, 10), Process("B", 3, 1)])
        segments = [(s["pid"], s["start_time"], s["end_time"], s["queue_level"]) for s in result["timeline"]]
        self.assertEqual(segments[:3], [("A", 0, 2, 0), ("A", 2, 3, 1), ("B", 3, 4, 0)])
        self.assertEqual(segments[3][0:3], ("A", 4, 7))

    def test_idle_period(self):
        result = MLFQScheduler().run([Process("late", 5, 2)])
        self.assertEqual(result["idle_periods"], [{"start_time": 0, "end_time": 5}])
        self.assertEqual(result["processes"][0]["completion_time"], 7)
        self.assertAlmostEqual(result["cpu_utilization"], 2 / 7 * 100)

    def test_simultaneous_arrivals_are_deterministic(self):
        result = MLFQScheduler([1, 2], boost_interval=None).run([Process("B", 0, 2), Process("A", 0, 2)])
        self.assertEqual([s["pid"] for s in result["timeline"][:2]], ["A", "B"])

    def test_priority_boosting(self):
        result = MLFQScheduler([1, 2, 4], boost_interval=3).run([Process("long", 0, 9), Process("other", 0, 5)])
        self.assertIn(3, result["boost_events"])
        self.assertTrue(all(p["completion_time"] is not None for p in result["processes"]))

    def test_boosts_during_idle_are_exact_and_idle_is_merged(self):
        result = MLFQScheduler([2, 4], boost_interval=3).run([Process("late", 10, 1)])
        self.assertEqual(result["boost_events"], [3, 6, 9])
        self.assertEqual(result["idle_periods"], [{"start_time": 0, "end_time": 10}])

    def test_boosting_disabled(self):
        result = MLFQScheduler([1, 2], boost_interval=None).run([Process("P", 0, 5)])
        self.assertEqual(result["boost_events"], [])

    def test_workload_is_reusable(self):
        source = [Process("P", 0, 7)]
        first = MLFQScheduler([1, 2]).run(source)
        second = MLFQScheduler([3, 6]).run(source)
        self.assertEqual(source[0].remaining_burst_time, 7)
        self.assertIsNone(source[0].completion_time)
        self.assertNotEqual(first["timeline"], second["timeline"])

    def test_process_metric_formulas(self):
        result = MLFQScheduler([10]).run([Process("A", 0, 3), Process("B", 2, 2)])
        by_pid = {p["pid"]: p for p in result["processes"]}
        self.assertEqual((by_pid["B"]["completion_time"], by_pid["B"]["turnaround_time"], by_pid["B"]["waiting_time"], by_pid["B"]["response_time"]), (5, 3, 1, 1))
        self.assertEqual(result["cpu_utilization"], 100)
        self.assertEqual(result["throughput"], 2 / 5)

    def test_finishing_exactly_at_quantum(self):
        result = MLFQScheduler([2, 4]).run([Process("P", 0, 2)])
        self.assertEqual(len(result["timeline"]), 1)
        self.assertEqual(result["timeline"][0]["queue_level"], 0)

    def test_invalid_inputs(self):
        for args in [("P", -1, 2), ("P", 0, 0), ("P", 0, -3), ("P", float("inf"), 2)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                Process(*args)
        for quanta in ([], [2, 0]):
            with self.subTest(quanta=quanta), self.assertRaises(ValueError):
                MLFQScheduler(quanta)
        with self.assertRaises(ValueError):
            MLFQScheduler([1], boost_interval=0)

    def test_duplicate_ids_and_non_process(self):
        with self.assertRaises(ValueError):
            MLFQScheduler().run([Process("P", 0, 1), Process("P", 2, 1)])
        with self.assertRaises(ValueError):
            MLFQScheduler().run(["not a process"])

    def test_configuration_update(self):
        scheduler = MLFQScheduler([1, 2], boost_interval=None)
        scheduler.configure(quanta=[4, 8, 16], boost_interval=30)
        self.assertEqual(scheduler.quanta, [4, 8, 16])
        self.assertEqual(scheduler.boost_interval, 30)
        scheduler.configure(boost_interval=None)
        self.assertIsNone(scheduler.boost_interval)

    def test_example_metrics_consistency(self):
        result = MLFQScheduler([2, 4, 8], boost_interval=20).run([Process("P1", 0, 10), Process("P2", 1, 4), Process("P3", 2, 6)])
        self.assertEqual(len(result["processes"]), 3)
        self.assertTrue(all(p["remaining_burst_time"] == 0 for p in result["processes"]))
        self.assertEqual(sum(s["duration"] for s in result["timeline"]), 20)
        for p in result["processes"]:
            self.assertEqual(p["turnaround_time"], p["completion_time"] - p["arrival_time"])
            self.assertEqual(p["waiting_time"], p["turnaround_time"] - p["burst_time"])
            self.assertEqual(p["response_time"], p["start_time"] - p["arrival_time"])


if __name__ == "__main__":
    unittest.main()
