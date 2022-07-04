from typing import (
    Any,
    Callable,
    Iterable,
    Literal,
    Mapping,
    Optional,
    Type,
    Union,
    overload,
)

from ._store import Processor, ProviderProcessorIterable, Store, T


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
        processors: Union[Mapping[object, Callable], ProviderProcessorIterable],
        *,
        store: Union[str, Store, None] = None,
    ):
        self._store = store if isinstance(store, Store) else Store.get_store(store)
        self._dispose = self._store.register_processors(processors)

    def __enter__(self) -> Store:
        return self._store

    def __exit__(self, *_: Any) -> None:
        self._dispose()


def iter_processors(
    type_: Union[object, Type[T]], store: Union[str, Store, None] = None
) -> Iterable[Callable[[T], Any]]:
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
    yield from store.iter_processors(type_)  # type: ignore # ???


# Decorator


@overload
def processor(
    func: Processor,
    *,
    weight: float = 0,
    for_type: Optional[object] = None,
    store: Union[str, Store, None] = None,
) -> Processor:
    ...


@overload
def processor(
    func: Literal[None] = ...,
    *,
    weight: float = 0,
    for_type: Optional[object] = None,
    store: Union[str, Store, None] = None,
) -> Callable[[Processor], Processor]:
    ...


def processor(
    func: Optional[Processor] = None,
    *,
    weight: float = 0,
    for_type: Optional[object] = None,
    store: Union[str, Store, None] = None,
) -> Union[Callable[[Processor], Processor], Processor]:
    """Decorate `func` as a processor of its first parameter type.

    Parameters
    ----------
    func : Optional[Processor], optional
        A function to decorate. If not provided, a decorator is returned.
    weight : float, optional
        A weight with which to sort this processor. Higher weights are given
        priority, by default 0.  When invoking processors, all processors
        will be invoked in descending weight order, unless `first_processor_only`
        is set to `True`.
    for_type : Optional[object]
        Optional type or type hint that this processor can handle. If not
        provided, the type hint of the first parameter of `func` will be used.
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
    store = store if isinstance(store, Store) else Store.get_store(store)
    return store.processor(func, weight=weight, for_type=for_type)
