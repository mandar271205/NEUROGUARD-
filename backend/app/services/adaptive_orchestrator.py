from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp
from typing import Any

import numpy as np


@dataclass(frozen=True)
class AdaptiveWeightingConfig:
    window_size: int = 50
    min_window_for_adaptive: int = 10
    cold_start_weight_baseline: float = 0.7
    cold_start_weight_neuroguard: float = 0.3
    critical_health_threshold: float = 0.2
    fallback_weight_baseline: float = 0.95
    fallback_weight_neuroguard: float = 0.05
    neuroguard_boost_factor: float = 1.5
    health_variance_weight: float = 0.5
    health_range_weight: float = 0.3
    health_mode_penalty_weight: float = 0.2
    expected_var_baseline: float = 0.05
    expected_var_neuroguard: float = 0.05
    expected_range: float = 0.6


@dataclass
class ModelHealth:
    score: float
    variance: float
    variance_score: float
    range_spread: float
    range_score: float
    mode_frequency: float
    mode_penalty: float
    sample_count: int


@dataclass
class OrchestrationResult:
    final_stress: float
    weight_baseline: float
    weight_neuroguard: float
    health_baseline: ModelHealth
    health_neuroguard: ModelHealth
    mode: str
    window_scope: str
    window_size: int


class AdaptiveWeightingEngine:
    GLOBAL_KEY = "__global__"

    def __init__(self, config: AdaptiveWeightingConfig | None = None) -> None:
        self.config = config or AdaptiveWeightingConfig()
        self._windows: defaultdict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=self.config.window_size)
        )

    def combine(
        self,
        baseline: float,
        neuroguard: float,
        student_id: str | None = None,
        baseline_weight_override: float | None = None,
    ) -> OrchestrationResult:
        baseline = float(np.clip(baseline, 0.0, 1.0))
        neuroguard = float(np.clip(neuroguard, 0.0, 1.0))

        scope_key = student_id or self.GLOBAL_KEY
        history, scope = self._select_history(scope_key)
        baseline_scores = [float(item["baseline"]) for item in history]
        neuroguard_scores = [float(item["neuroguard"]) for item in history]
        health_baseline = self.health_score(baseline_scores, self.config.expected_var_baseline)
        health_neuroguard = self.health_score(neuroguard_scores, self.config.expected_var_neuroguard)

        weight_baseline, weight_neuroguard, mode = self._weights(
            health_baseline.score,
            health_neuroguard.score,
            len(history),
            baseline_weight_override,
        )
        final_stress = float(np.clip(weight_baseline * baseline + weight_neuroguard * neuroguard, 0.0, 1.0))

        result = OrchestrationResult(
            final_stress=final_stress,
            weight_baseline=weight_baseline,
            weight_neuroguard=weight_neuroguard,
            health_baseline=health_baseline,
            health_neuroguard=health_neuroguard,
            mode=mode,
            window_scope=scope,
            window_size=len(history),
        )
        self._append(scope_key, baseline, neuroguard, result)
        return result

    def health_score(self, scores: list[float], expected_var: float) -> ModelHealth:
        if len(scores) < 2:
            return ModelHealth(
                score=0.0,
                variance=0.0,
                variance_score=0.0,
                range_spread=0.0,
                range_score=0.0,
                mode_frequency=1.0 if scores else 0.0,
                mode_penalty=0.0,
                sample_count=len(scores),
            )

        values = np.asarray(scores, dtype=float)
        variance = float(np.var(values))
        variance_score = float(np.clip(variance / max(expected_var, 1e-9), 0.0, 1.0))
        range_spread = float(np.max(values) - np.min(values))
        range_score = float(np.clip(range_spread / max(self.config.expected_range, 1e-9), 0.0, 1.0))
        _, counts = np.unique(np.round(values, 2), return_counts=True)
        mode_frequency = float(np.max(counts) / len(values))
        mode_penalty = float(np.clip(1.0 - max(0.0, mode_frequency - 0.4) / 0.6, 0.0, 1.0))
        total_weight = (
            self.config.health_variance_weight
            + self.config.health_range_weight
            + self.config.health_mode_penalty_weight
        )
        if total_weight <= 0:
            total_weight = 1.0
        score = float(
            np.clip(
                (
                    self.config.health_variance_weight * variance_score
                    + self.config.health_range_weight * range_score
                    + self.config.health_mode_penalty_weight * mode_penalty
                )
                / total_weight,
                0.0,
                1.0,
            )
        )
        return ModelHealth(
            score=score,
            variance=variance,
            variance_score=variance_score,
            range_spread=range_spread,
            range_score=range_score,
            mode_frequency=mode_frequency,
            mode_penalty=mode_penalty,
            sample_count=len(scores),
        )

    def _select_history(self, scope_key: str) -> tuple[deque[dict[str, Any]], str]:
        student_window = self._windows[scope_key]
        global_window = self._windows[self.GLOBAL_KEY]
        if scope_key != self.GLOBAL_KEY and len(student_window) >= self.config.min_window_for_adaptive:
            return student_window, "student"
        if len(global_window) >= self.config.min_window_for_adaptive:
            return global_window, "global"
        return student_window, "student_cold_start" if scope_key != self.GLOBAL_KEY else "global_cold_start"

    def _weights(
        self,
        health_baseline: float,
        health_neuroguard: float,
        history_size: int,
        baseline_weight_override: float | None,
    ) -> tuple[float, float, str]:
        if baseline_weight_override is not None:
            weight_baseline = float(np.clip(baseline_weight_override, 0.0, 1.0))
            return weight_baseline, 1.0 - weight_baseline, "manual_override"

        if history_size < self.config.min_window_for_adaptive:
            return (
                self.config.cold_start_weight_baseline,
                self.config.cold_start_weight_neuroguard,
                "cold_start",
            )

        if health_neuroguard < self.config.critical_health_threshold:
            return (
                self.config.fallback_weight_baseline,
                self.config.fallback_weight_neuroguard,
                "neuroguard_health_fallback",
            )

        raw_baseline = health_baseline
        raw_neuroguard = health_neuroguard * self.config.neuroguard_boost_factor
        exp_baseline = exp(raw_baseline)
        exp_neuroguard = exp(raw_neuroguard)
        weight_baseline = float(exp_baseline / (exp_baseline + exp_neuroguard))
        return weight_baseline, 1.0 - weight_baseline, "adaptive"

    def _append(
        self,
        scope_key: str,
        baseline: float,
        neuroguard: float,
        result: OrchestrationResult,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "baseline": baseline,
            "neuroguard": neuroguard,
            "final": result.final_stress,
            "w_b": result.weight_baseline,
            "w_n": result.weight_neuroguard,
            "health_b": result.health_baseline.score,
            "health_n": result.health_neuroguard.score,
            "mode": result.mode,
        }
        self._windows[scope_key].append(entry)
        if scope_key != self.GLOBAL_KEY:
            self._windows[self.GLOBAL_KEY].append(entry)
