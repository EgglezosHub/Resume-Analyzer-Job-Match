import numpy as np


def cosine(a, b) -> float:
	a = np.array(a)
	b = np.array(b)
	denom = (np.linalg.norm(a) * np.linalg.norm(b))
	if denom == 0:
		return 0.0
	return float(np.dot(a, b) / denom)


def jaccard(a: set[str], b: set[str]) -> float:
	if not a and not b:
		return 0.0
	return len(a & b) / len(a | b)
