import warnings
from typing import (
    Any,
    Callable,
    Literal,
    Mapping,
    Optional,
    Type,
    Union,
    cast,
    get_type_hints,
    overload,
)

from ._store import Processor, Store, T


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
    store : Union[str, Store, None]
        The processor store to use, if not provided the global store is used.

    Raises
    ------
    ValueError
        if clobber is `True` and one of the keys in `mapping` is already
        registered.
    """

    def __init__(
        self,
        mapping: Mapping[Union[Type[T], object], Callable[[T], Any]],
        *,
        clobber: bool = False,
        store: Union[str, Store, None] = None,
    ):
        self._store = store if isinstance(store, Store) else Store.get_store(store)
        self._before = self._store._set_processor(mapping, clobber=clobber)

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: Any) -> None:
        for origin, val in self._before.items():
            if val is self._store._NULL:
                del self._store.processors[origin]
            else:
                self._store.processors[origin] = cast(Callable, val)


def get_processor(
    type_: Union[Type[T], object],
    store: Union[str, Store, None] = None,
) -> Optional[Callable[[T], Any]]:
    """Return processor function for a given type.

    A processor is a function that can "process" a given return type.  The term
    process here leaves a lot of ambiguity, it mostly means the function "can
    do something" with a single input of the given type.

    Parameters
    ----------
    type_ : Type[T]
        Type for which to get the processor.
    store : Union[str, Store, None]
        The processor store to use, if not provided the global store is used.

    Returns
    -------
    Optional[Callable[[T], Any]]
        A processor function registered for `type_`, if any.

    Examples
    --------
    >>> get_processor(int)
    """
    store = store if isinstance(store, Store) else Store.get_store(store)
    return store._get_processor(type_)


def clear_processor(
    type_: Union[object, Type[T]],
    warn_missing: bool = False,
    store: Union[str, Store, None] = None,
) -> Optional[Callable[[T], Any]]:
    """Clear processor for a given type.

    Note: this does NOT yet clear sub/superclasses of type_. So if there is a registered
    processor for `Sequence`, and you call `clear_processor(list)`, the `Sequence`
    processor will still be registered, and vice versa.

    Parameters
    ----------
    type_ : Type[T]
        The processor type to clear
    warn_missing : bool, optional
        Whether to emit a warning if there was not type registered, by default False
    store : Union[str, Store, None]
        The processor store to use, if not provided the global store is used.

    Returns
    -------
    Optional[Callable[[], T]]
        The processor function that was cleared, if any.
    """
    store = store if isinstance(store, Store) else Store.get_store(store)
    result = store._pop_processor(type_)

    if result is None and warn_missing:
        warnings.warn(
            f"No processor was registered for {type_}, and warn_missing is True."
        )
    return result


# Decorator


@overload
def processor(func: Processor, *, store: Union[str, Store, None] = None) -> Processor:
    ...


@overload
def processor(
    func: Literal[None] = ..., *, store: Union[str, Store, None] = None
) -> Callable[[Processor], Processor]:
    ...


def processor(
    func: Optional[Processor] = None, *, store: Union[str, Store, None] = None
) -> Union[Callable[[Processor], Processor], Processor]:
    """Decorate `func` as a processor of its first parameter type.

    Parameters
    ----------
    func : Optional[Processor], optional
        A function to decorate. If not provided, a decorator is returned.
    store : Union[str, Store, None]
        The processor store to use, if not provided the global store is used.

    Returns
    -------
    Union[Callable[[Processor], Processor], Processor]
        If `func` is not provided, a decorator is returned, if `func` is provided
        then the function is returned.

    Examples
    --------
    >>> @processor
    >>> def process_int(x: int) -> None:
    ...     print("Processing int:", x)
    """

    def _inner(func: Processor) -> Processor:
        hints = get_type_hints(func)
        hints.pop("return", None)
        if not hints:
            warnings.warn(f"{func} has no argument type hints. Cannot be a processor.")
            return func

        hint0 = list(hints.values())[0]
        set_processors({hint0: func}, store=store)
        return func

    return _inner(func) if func is not None else _inner
