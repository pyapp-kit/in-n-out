from typing import Any, Callable, Iterable, Literal, Optional, Type, Union, overload

from ._store import Processor, Store, T


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
