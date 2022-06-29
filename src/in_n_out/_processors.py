import warnings
from typing import (
    Any,
    Callable,
    Mapping,
    Optional,
    Type,
    Union,
    cast,
    get_type_hints,
    overload,
)

from ._store import _STORE, Processor, T


def processor(func: Processor) -> Processor:
    """Decorator that declares `func` as a processor of its first parameter type."""
    hints = get_type_hints(func)
    hints.pop("return", None)
    if not hints:
        warnings.warn(f"{func} has no argument type hints. Cannot be a processor.")
        return func

    hint0 = list(hints.values())[0]
    set_processors({hint0: func})
    return func


def get_processor(type_: Type[T]) -> Optional[Callable[[T], Any]]:
    """Return processor function for a given type.

    A processor is a function that can "process" a given return type.  The term
    process here leaves a lot of ambiguity, it mostly means the function "can
    do something" with a single input of the given type.
    """
    return _STORE._get(type_, provider=False, pop=False)


@overload
def clear_processor(type_: Type[T]) -> Union[Callable[[], T], None]:
    ...


@overload
def clear_processor(type_: object) -> Union[Callable[[], Optional[T]], None]:
    ...


def clear_processor(
    type_: Union[object, Type[T]], warn_missing: bool = False
) -> Union[Callable[[], T], Callable[[], Optional[T]], None]:
    """Clear provider for a given type.

    Note: this does NOT yet clear sub/superclasses of type_. So if there is a registered
    provider for Sequence, and you call clear_processor(list), the Sequence provider
    will still be registered, and vice versa.

    Parameters
    ----------
    type_ : Type[T]
        The provider type to clear
    warn_missing : bool, optional
        Whether to emit a warning if there was not type registered, by default False

    Returns
    -------
    Optional[Callable[[], T]]
        The provider function that was cleared, if any.
    """
    result = _STORE._get(type_, provider=False, pop=True)

    if result is None and warn_missing:
        warnings.warn(
            f"No processor was registered for {type_}, and warn_missing is True."
        )
    return result


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
        self, mapping: Mapping[Any, Callable[[T], Any]], clobber: bool = False
    ):
        self._before = _STORE._set(mapping, provider=False, clobber=clobber)

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: Any) -> None:

        for (type_, _), val in self._before.items():
            MAP: dict = _STORE.processors
            if val is _STORE._NULL:
                del MAP[type_]
            else:
                MAP[type_] = cast(Callable, val)
