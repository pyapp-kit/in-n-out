from functools import wraps
from typing import Callable, Generator, Iterable, TypeVar

from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def _wrap_generator(
    func: Callable, _exec: Callable[P, Iterable[R]]
) -> Callable[P, Generator[R, None, None]]:
    @wraps(func)
    def _gexec(*args: P.args, **kwargs: P.kwargs) -> Generator[R, None, None]:
        yield from _exec(*args, **kwargs)

    return _gexec
