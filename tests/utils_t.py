import unittest
import os
import time
import logging
import concurrent.futures

from manager import compress_and_dumps, decompress_and_loads


class UtilsTest(unittest.TestCase):

    def test_serialization(self):
        def f(x):
            return x+1
        compressed = compress_and_dumps(f)
        fprime = decompress_and_loads(compressed)
        self.assertEqual(fprime(1), 2)

    def test_serialization_global(self):
        a = 1

        def f(x):
            return x+a
        compressed = compress_and_dumps(f)
        a = 2
        fprime = decompress_and_loads(compressed)
        self.assertEqual(fprime(1), 3)


if __name__ == "__main__":
    unittest.main()
