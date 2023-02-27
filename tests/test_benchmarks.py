from __future__ import annotations

import sys
from typing import Callable

import pytest

import in_n_out as ino

if all(x not in {"--codspeed", "--benchmark", "tests/test_bench.py"} for x in sys.argv):
    pytest.skip("use --benchmark to run benchmark", allow_module_level=True)


def some_func(x: int, y: str) -> tuple[int, str]:
    return x, y


def returns_str(x: int, y: str) -> str:
    return str(x) + y


def test_time_to_inject(benchmark: Callable) -> None:
    benchmark(ino.inject, some_func)


def test_time_run_injected_no_injections(benchmark: Callable) -> None:
    injected = ino.inject(some_func)
    benchmark(injected, 1, "a")


def test_time_run_injected_2_injections(benchmark: Callable) -> None:
    injected = ino.inject(some_func)
    with ino.register(providers=[(lambda: 1, int), (lambda: "a", str)]):
        benchmark(injected)


def test_time_run_process(benchmark: Callable) -> None:
    injected = ino.inject_processors(returns_str)
    with ino.register(processors=[(lambda x: print(x), str)]):
        benchmark(injected, 1, "hi")


def test_time_run_inject_and_process(benchmark: Callable) -> None:
    injected = ino.inject(returns_str, processors=True)
    with ino.register(
        providers=[(lambda: "a", str)], processors=[(lambda x: ..., str)]
    ):
        benchmark(injected, 1)
