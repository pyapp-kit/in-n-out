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

from ._store import Provider, ProviderProcessorIterable, Store, T


class set_providers:
    """Set provider(s) for given type(s).

    "Providers" are functions that can retrieve an instance of a given type.

    This is a class that behaves as a function or a context manager, that
    allows one to set a provider function for a given type temporarily.

    If not used as a context, the provider function is set permanently.

    Parameters
    ----------
    providers : Union[Mapping[object, Callable], ProviderProcessorIterable]
        Either a mapping of {type_hint: provider} pairs, or an iterable of
        (type_hint, provider) or (type_hint, provider, weight) tuples.
    store : Union[str, Store, None]
        The provider store to use, if not provided the global store is used.
    """

    def __init__(
        self,
        providers: Union[Mapping[object, Callable], ProviderProcessorIterable],
        *,
        store: Union[str, Store, None] = None,
    ) -> None:
        self._store = store if isinstance(store, Store) else Store.get_store(store)
        self._dispose = self._store.register_providers(providers)

    def __enter__(self) -> Store:
        return self._store

    def __exit__(self, *_: Any) -> None:
        self._dispose()


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
