import unittest
import os
import time
import logging
import concurrent.futures

from worker import Worker
from manager import Manager
from config import REDIS_URL

def run_one_worker(i): 
    w = Worker(REDIS_URL,verbose=False).run()

class ManagerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.num_workers = 4
        executor = concurrent.futures.ProcessPoolExecutor(cls.num_workers)
        cls.worker_futures = [executor.submit(run_one_worker,i) for i in range(cls.num_workers)]
        cls.m = Manager(REDIS_URL)

    def test_connectivity(self):
        results = self.m.remote_map(lambda x:x, range(self.num_workers*2),return_metadata=True)
        worker_names = set([r[1]["worker_name"] for r in results])
        self.assertEqual(len(worker_names),self.num_workers)

    @classmethod
    def tearDownClass(cls):
        results = cls.m.remote_map(lambda x:x, ["STOP" for _ in range(cls.num_workers)])

if __name__ == "__main__":
    unittest.main()
