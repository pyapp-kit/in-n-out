# flake8: noqa
from typing import Tuple

import in_n_out as ino


def some_func(x: int, y: str) -> Tuple[int, str]:
    return x, y


class ConnectSuite:
    # params = [1, 10, 100]

    def setup(self):
        self.reg_func = some_func
        self.injected_func = ino.inject_dependencies(some_func)
        ino.set_providers({int: lambda: 1, str: lambda: "hi"}, clobber=True)

    def time_to_inject(self):
        ino.inject_dependencies(some_func)

    def time_run_reg_func(self):
        assert self.reg_func(1, "hi") == (1, "hi")

    def time_run_injected_func(self):
        assert self.injected_func() == (1, "hi")
