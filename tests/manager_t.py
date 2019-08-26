import unittest
import os
import time
import logging
import concurrent.futures

import numpy as np

from worker import Worker
from manager import Manager
from config import REDIS_URL

def run_one_worker(i): 
    w = Worker(REDIS_URL,verbose=False).run()

def start_workers(n):
    executor = concurrent.futures.ProcessPoolExecutor(n)
    worker_futures = [executor.submit(run_one_worker,i) for i in range(n)]
    return executor, worker_futures

class ManagerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Manager(REDIS_URL, progress_bars=False)

    def test_local_map(self):
        results = self.m.local_map(lambda x:x, range(5))
        self.assertEqual(set(results),set(range(5)))

    def test_one_worker(self):
        executor, futures = start_workers(1)
        time.sleep(0.2)
        results = self.m.remote_map(lambda x:x, range(5), return_metadata=False)
        self.assertEqual(set(results),set(range(5)))
        self.m.stop_all_workers()

    def test_few_workers(self):
        num_workers = 8
        executor, futures = start_workers(num_workers)
        time.sleep(0.2)

        results = self.m.remote_map(lambda x:time.sleep(0.1), range(num_workers*2), return_metadata=True)
        worker_names = set([r[1]["worker_name"] for r in results])
        self.assertEqual(len(worker_names),num_workers)
        self.assertEqual(len(self.m.get_worker_info()),num_workers)

        self.m.stop_all_workers()
        self.assertEqual(len(self.m.get_worker_info()),0)

    def test_worker_scheduling(self):
        num_workers = 4
        executor, futures = start_workers(num_workers)
        time.sleep(0.2)

        all_worker_names = self.m.get_worker_info().index
        results = self.m.remote_map(lambda x:x, all_worker_names,
                worker_names=all_worker_names,return_metadata=True)
        self.assertEqual(
                [r[0] for r in results],
                [r[1]["worker_name"] for r in results]
                )
        self.m.stop_all_workers()

    def test_nonblocking(self):
        num_workers = 4
        executor, futures = start_workers(num_workers)
        time.sleep(0.2)
        results_generator = self.m.remote_map(lambda x:time.sleep(0.1), range(10),
                return_metadata=True, blocking=False)
        self.assertFalse(hasattr(results_generator,"__len__"))
        results = list(results_generator)
        self.assertEqual(len(results),10)
        self.m.stop_all_workers()

    def test_payload_size_limits(self):
        executor, futures = start_workers(1)
        time.sleep(0.2)
        # Make a function that has 5MB worth of random floats
        # so that it doesn't get compressed below 5MB
        # This should trigger the safeguard in remote_map
        nbytes = 5e6
        def f(x,y=np.random.random(int(nbytes//8))):
            return x+1
        with self.assertRaises(RuntimeError):
            self.m.remote_map(f, [None])
        self.m.stop_all_workers()

    @classmethod
    def tearDownClass(cls):
        cls.m.stop_all_workers()

if __name__ == "__main__":
    unittest.main()
