from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, get_origin

from typing_extensions import get_args, get_type_hints

T = TypeVar("T")
C = TypeVar("C", bound=Callable)
_NULL = object()

# add default processors
_PROCESSORS: Dict[Any, Callable[[Any], Any]] = {}


def processor(func: C) -> C:
    """Decorator that declares `func` as a processor of its first parameter type."""
    hints = get_type_hints(func)
    hints.pop("return", None)
    if not hints:  # pragma: no cover
        raise TypeError(f"{func} has no argument type hints. Cannot be a processor.")
    hint0 = list(hints.values())[0]

    if hint0 is not None:
        if get_origin(hint0) == Union:
            for arg in get_args(hint0):
                if arg is not None:
                    _PROCESSORS[arg] = func
        else:
            _PROCESSORS[hint0] = func
    return func


def get_processor(type_: Type[T]) -> Optional[Callable[[T], Any]]:
    """Return processor function for a given type.

    A processor is a function that can "process" a given return type.  The term
    process here leaves a lot of ambiguity, it mostly means the function "can
    do something" with a single input of the given type.
    """
    if type_ in _PROCESSORS:
        return _PROCESSORS[type_]

    if isinstance(type_, type):
        for key, val in _PROCESSORS.items():
            if isinstance(key, type) and issubclass(type_, key):
                return val  # type: ignore [return-type]


class set_processors:
    """Set processor(s) for given type(s).

    "Processors" are functions that can "do something" with an instance of the
    type that they support.

    This is a class that behaves as a function or a context manager, that
    allows one to set a processor function for a given type.

    Parameters
    ----------
    mapping : Dict[Type[T], Callable[..., Optional[T]]]
        a map of type -> processor function, where each value is a function
        that is capable of retrieving an instance of the associated key/type.
    clobber : bool, optional
        Whether to override any existing processor function, by default False.

    Raises
    ------
    ValueError
        if clobber is `True` and one of the keys in `mapping` is already
        registered.
    """

    def __init__(
        self, mapping: Dict[Type[T], Callable[..., Optional[T]]], clobber=False
    ):
        self._before = {}
        for k in mapping:
            if k in _PROCESSORS and not clobber:
                raise ValueError(
                    f"Class {k} already has a processor and clobber is False"
                )
            self._before[k] = _PROCESSORS.get(k, _NULL)
        _PROCESSORS.update(mapping)

    def __enter__(self):
        return None

    def __exit__(self, *_):
        for key, val in self._before.items():
            if val is _NULL:
                del _PROCESSORS[key]
            else:
                _PROCESSORS[key] = val
