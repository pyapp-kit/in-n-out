import warnings
from typing import (
    Any,
    Callable,
    Dict,
    Literal,
    Optional,
    Type,
    Union,
    cast,
    get_type_hints,
    overload,
)

from ._store import Provider, Store, T


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
        mapping: Dict[Union[Type[T], object], Union[T, Callable[[], T]]],
        *,
        clobber: bool = False,
        store: Union[str, Store, None] = None,
    ) -> None:
        self._store = store if isinstance(store, Store) else Store.get_store(store)
        self._before = self._store._set_provider(mapping, clobber=clobber)

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: Any) -> None:
        for (type_, optional), val in self._before.items():
            MAP: dict = self._store.opt_providers if optional else self._store.providers
            if val is self._store._NULL:
                del MAP[type_]
            else:
                MAP[type_] = cast(Callable, val)


@overload
def get_provider(
    type_: Type[T], store: Union[str, Store, None] = None
) -> Union[Callable[[], T], None]:
    ...


@overload
def get_provider(
    type_: object, store: Union[str, Store, None] = None
) -> Union[Callable[[], Optional[T]], None]:
    # `object` captures passing get_provider(Optional[type])
    ...


def get_provider(
    type_: Union[object, Type[T]], store: Union[str, Store, None] = None
) -> Union[Callable[[], T], Callable[[], Optional[T]], None]:
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
    return store._get_provider(type_)


@overload
def clear_provider(
    type_: Type[T],
    warn_missing: bool = False,
    store: Union[str, Store, None] = None,
) -> Union[Callable[[], T], None]:
    ...


@overload
def clear_provider(
    type_: object,
    warn_missing: bool = False,
    store: Union[str, Store, None] = None,
) -> Union[Callable[[], Optional[T]], None]:
    ...


def clear_provider(
    type_: Union[object, Type[T]],
    warn_missing: bool = False,
    store: Union[str, Store, None] = None,
) -> Union[Callable[[], T], Callable[[], Optional[T]], None]:
    """Clear provider for a given type.

    Note: this does NOT yet clear sub/superclasses of type_. So if there is a registered
    provider for Sequence, and you call clear_provider(list), the Sequence provider
    will still be registered, and vice versa.

    Parameters
    ----------
    type_ : Type[T]
        The provider type to clear
    warn_missing : bool, optional
        Whether to emit a warning if there was not type registered, by default False
    store : Union[str, Store, None]
        The provider store to use, if not provided the global store is used.

    Returns
    -------
    Optional[Callable[[], T]]
        The provider function that was cleared, if any.
    """
    store = store if isinstance(store, Store) else Store.get_store(store)
    result = store._pop_provider(type_)

    if result is None and warn_missing:
        warnings.warn(
            f"No provider was registered for {type_}, and warn_missing is True."
        )
    return result


# Decorator


@overload
def provider(func: Provider, *, store: Union[str, Store, None] = None) -> Provider:
    ...


@overload
def provider(
    func: Literal[None] = ..., *, store: Union[str, Store, None] = None
) -> Callable[[Provider], Provider]:
    ...


def provider(
    func: Optional[Provider] = None, *, store: Union[str, Store, None] = None
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

    def _inner(func: Provider) -> Provider:
        return_hint = get_type_hints(func).get("return")
        if return_hint is None:
            warnings.warn(f"{func} has no return type hint. Cannot be a provider.")
        else:
            set_providers({return_hint: func}, store=store)
        return func

    return _inner(func) if func is not None else _inner
