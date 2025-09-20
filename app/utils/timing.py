import time
from contextlib import contextmanager


@contextmanager
def timer():
	start = time.perf_counter()
	yield lambda: int((time.perf_counter() - start) * 1000)
