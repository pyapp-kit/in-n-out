# flake8: noqa
from typing import Tuple

import in_n_out as ino

if hasattr(ino, "inject_dependencies"):
    _inject = ino.inject_dependencies  # old API
else:
    _inject = ino.inject


def some_func(x: int, y: str) -> Tuple[int, str]:
    return x, y


class ConnectSuite:
    # params = [1, 10, 100]

    def setup(self):
        self.reg_func = some_func
        self.injected_func = _inject(some_func)

    def time_to_inject(self):
        _inject(some_func)

    def time_run_reg_func(self):
        self.reg_func(1, "a")

    def time_run_injected_func(self):
        self.injected_func(1, "a")
