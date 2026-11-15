"""Predictive regret matching+, vectorized over many infosets."""
from __future__ import annotations

import numpy as np


class PredictiveRegretMatchingPlus:
    def __init__(self, slot_infoset: np.ndarray, n_infosets: int, initial: np.ndarray):
        self.slot_infoset = slot_infoset
        self.n_infosets = n_infosets
        self.regret = np.zeros(len(slot_infoset))
        self.strategy = initial.astype(float)

    def update(self, utility: np.ndarray) -> None:
        expected = self._per_infoset(self.strategy * utility)
        instant = utility - expected
        self.regret = np.maximum(self.regret + instant, 0.0)
        self.strategy = self._normalize(np.maximum(self.regret + instant, 0.0))

    def _per_infoset(self, values: np.ndarray) -> np.ndarray:
        """Sum ``values`` within each infoset and broadcast the sum back to its slots."""
        totals = np.bincount(self.slot_infoset, weights=values, minlength=self.n_infosets)
        return totals[self.slot_infoset]

    def _normalize(self, weights: np.ndarray) -> np.ndarray:
        totals = self._per_infoset(weights)
        positive = totals > 0
        return np.where(positive, weights / np.where(positive, totals, 1.0), self.strategy)


def best_action_strategy(value: np.ndarray, infoset_start: np.ndarray) -> np.ndarray:
    """All mass on the highest-``value`` slot of each infoset."""
    strategy = np.zeros(len(value))
    ends = np.append(infoset_start[1:], len(value))
    for start, end in zip(infoset_start, ends, strict=True):
        strategy[start + np.argmax(value[start:end])] = 1.0
    return strategy
