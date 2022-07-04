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
    allows one to set a provider function for a given type.

    Parameters
    ----------
    mapping : Dict[Type[T], Callable[..., Optional[T]]]
        a map of type -> provider function, where each value is a function
        that is capable of retrieving an instance of the associated key/type.
    clobber : bool, optional
        Whether to override any existing provider function, by default False.
    store : Union[str, Store, None]
        The provider store to use, if not provided the global store is used.

    Raises
    ------
    ValueError
        if clobber is `False` and one of the keys in `mapping` is already
        registered.
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
    """Return object provider function given a type.

    An object provider is a function that returns an instance of a
    particular object type.

    Parameters
    ----------
    type_ : Type[T] or Type Hint
        Type for which to get the provider.
    store : Union[str, Store, None]
        The provider store to use, if not provided the global store is used.

    Returns
    -------
    Optional[Callable[[T], Any]]
        A provider function registered for `type_`, if any.

    Examples
    --------
    >>> get_provider(int)
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
