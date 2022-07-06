from typing import Callable, Iterable, Literal, Optional, Type, Union, overload

from ._store import Provider, Store, T


def iter_providers(
    type_: Union[object, Type[T]], store: Union[str, Store, None] = None
) -> Iterable[Callable[[], Optional[T]]]:
    """Iterate over all providers of `type_`.

    Parameters
    ----------
    type_ : Union[object, Type[T]]
        A type or type hint for which to return providers.
    store : Union[str, Store, None]
        The provider store to use, if not provided the global store is used.

    Yields
    ------
    Iterable[Callable[[], Optional[T]]]
        Iterable of provider callbacks.
    """
    store = store if isinstance(store, Store) else Store.get_store(store)
    yield from store.iter_providers(type_)


# Decorator


@overload
def provider(
    func: Provider,
    *,
    weight: float = 0,
    for_type: Optional[object] = None,
    store: Union[str, Store, None] = None,
) -> Provider:
    ...


@overload
def provider(
    func: Literal[None] = ...,
    *,
    weight: float = 0,
    for_type: Optional[object] = None,
    store: Union[str, Store, None] = None,
) -> Callable[[Provider], Provider]:
    ...


def provider(
    func: Optional[Provider] = None,
    *,
    weight: float = 0,
    for_type: Optional[object] = None,
    store: Union[str, Store, None] = None,
) -> Union[Callable[[Provider], Provider], Provider]:
    """Decorate `func` as a provider of its first parameter type.

    Note, If func returns `Optional[Type]`, it will be registered as a provider
    for Type.

    Parameters
    ----------
    func : Optional[Provider], optional
        A function to decorate. If not provided, a decorator is returned.
    weight : float
        A weight with which to sort this provider. Higher weights are given
        priority, by default 0
    for_type : Optional[object]
        Optional type or type hint for which to register this provider. If not
        provided, the return annotation of `func` will be used.
    store : Union[str, Store, None]
        The Provider store to use, if not provided the global store is used.

    Returns
    -------
    Union[Callable[[Provider], Provider], Provider]
        If `func` is not provided, a decorator is returned, if `func` is provided
        then the function is returned..

    Examples
    --------
    >>> @provider
    >>> def provide_int() -> int:
    ...     return 42
    """
    store = store if isinstance(store, Store) else Store.get_store(store)
    return store.provider(func, weight=weight, for_type=for_type)
