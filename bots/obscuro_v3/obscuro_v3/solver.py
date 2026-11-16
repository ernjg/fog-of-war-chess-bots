"""Alternating PCFR+ on a Depth2Game; values are from our side."""
from __future__ import annotations

import numpy as np

from .regret import PredictiveRegretMatchingPlus, best_action_strategy
from .subgame import Depth2Game


class Depth2Solver:
    def __init__(self, game: Depth2Game):
        self.game = game
        self.iterations = 0
        self._leaf_root = game.leaf_node // game.n_actions
        self._leaf_action = game.leaf_node % game.n_actions
        self._is_terminal = ~np.isnan(game.terminal_value)
        self._terminal_value = np.nan_to_num(game.terminal_value)

        our_infoset = np.zeros(game.n_actions, dtype=np.int64)
        self.ours = PredictiveRegretMatchingPlus(
            our_infoset, 1, best_action_strategy(game.our_prior, np.array([0])))
        self.theirs = PredictiveRegretMatchingPlus(
            game.slot_infoset, len(game.infoset_start),
            best_action_strategy(-game.their_prior, game.infoset_start))

    def iterate(self) -> None:
        self.ours.update(self.our_action_values())
        self.theirs.update(-self._their_counterfactual_values())
        self.iterations += 1

    def our_action_values(self) -> np.ndarray:
        """Expected value of each of our moves under the opponent's current strategy."""
        return self.game.root_weight @ self._node_values().reshape(self.game.n_roots, -1)

    @property
    def value(self) -> float:
        return float(self.ours.strategy @ self.our_action_values())

    def nash_gap(self) -> float:
        """Our best-response value minus the opponent's; 0 exactly at equilibrium."""
        our_best = self.our_action_values().max()
        counterfactual = self._their_counterfactual_values()
        their_best = (np.minimum.reduceat(counterfactual, self.game.infoset_start).sum()
                      if len(counterfactual) else 0.0)
        terminal = self._reach_of_nodes() @ (self._is_terminal * self._terminal_value)
        return float(our_best - (their_best + terminal))

    def _node_values(self) -> np.ndarray:
        """Value of every opponent node under the opponent's current strategy."""
        leaf_weight = self.theirs.strategy[self.game.leaf_slot] * self.game.leaf_value
        values = np.bincount(self.game.leaf_node, weights=leaf_weight,
                             minlength=len(self.game.terminal_value))
        return np.where(self._is_terminal, self._terminal_value, values)

    def _their_counterfactual_values(self) -> np.ndarray:
        """Counterfactual value of each opponent reply, weighted by chance and our reach."""
        reach = (self.game.root_weight[self._leaf_root]
                 * self.ours.strategy[self._leaf_action])
        return np.bincount(self.game.leaf_slot, weights=reach * self.game.leaf_value,
                           minlength=len(self.game.slot_infoset))

    def _reach_of_nodes(self) -> np.ndarray:
        return np.outer(self.game.root_weight, self.ours.strategy).ravel()
