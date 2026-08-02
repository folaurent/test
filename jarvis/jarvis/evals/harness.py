"""Harness d'évals. Les golden tasks sont du YAML validé.

Chaque golden a :
  - id, agent, kind (conversation|reasoning|classification|voice|scope|disclosure)
  - input (texte/contexte)
  - expected_tags ou expected_contains ou expected_regex ou forbidden_contains
  - passing_score (0-1)

Promotion d'autonomie bloquée tant que score agrégé < charter.eval_threshold.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml


@dataclass
class GoldenTask:
    id: str
    agent: str
    kind: str
    input: str
    zone: str = "FR"
    venture: str = "transverse"
    expected_contains: list[str] = field(default_factory=list)
    expected_regex: list[str] = field(default_factory=list)
    forbidden_contains: list[str] = field(default_factory=list)
    passing_score: float = 1.0
    notes: str = ""


@dataclass
class EvalResult:
    golden_id: str
    passed: bool
    score: float
    detail: str = ""


@dataclass
class EvalReport:
    agent: str
    results: list[EvalResult]

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)


def _evaluate_text(g: GoldenTask, output: str) -> EvalResult:
    fails: list[str] = []
    for needle in g.expected_contains:
        if needle.lower() not in output.lower():
            fails.append(f"missing: '{needle}'")
    for pat in g.expected_regex:
        if not re.search(pat, output, re.IGNORECASE):
            fails.append(f"regex fail: {pat}")
    for banned in g.forbidden_contains:
        if banned.lower() in output.lower():
            fails.append(f"forbidden: '{banned}'")
    passed = not fails
    score = 1.0 if passed else max(0.0, 1.0 - 0.2 * len(fails))
    return EvalResult(
        golden_id=g.id,
        passed=passed and score >= g.passing_score,
        score=score,
        detail="; ".join(fails),
    )


class EvalHarness:
    def __init__(self, goldens_dir: Path | None = None) -> None:
        self._dir = goldens_dir or Path("goldens")

    def load(self, agent: str | None = None) -> list[GoldenTask]:
        tasks: list[GoldenTask] = []
        if not self._dir.exists():
            return tasks
        for path in self._dir.glob("*.yml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for raw in data.get("goldens", []):
                g = GoldenTask(**raw)
                if agent is None or g.agent == agent:
                    tasks.append(g)
        return tasks

    def run(
        self,
        agent: str,
        runner: Callable[[GoldenTask], str],
    ) -> EvalReport:
        tasks = self.load(agent)
        results = [_evaluate_text(g, runner(g)) for g in tasks]
        return EvalReport(agent=agent, results=results)
