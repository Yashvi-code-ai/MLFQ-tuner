import unittest
from mlfq import MLFQScheduler, Process

class BoostIdleTest(unittest.TestCase):
    def test_boost_events_during_idle(self):
        result = MLFQScheduler([2, 4], boost_interval=3).run([Process('late', 10, 1)])
        self.assertEqual(result['boost_events'], [3, 6, 9])
        self.assertEqual(result['idle_periods'], [{'start_time': 0, 'end_time': 10}])

if __name__ == '__main__':
    unittest.main()
