import warnings
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    Union,
    cast,
    get_type_hints,
    overload,
)

from ._store import _STORE, Provider, T


def provider(func: Provider) -> Provider:
    """Decorator that declares `func` as a provider of its return type.

    Note, If func returns `Optional[Type]`, it will be registered as a provider
    for Type.

    Examples
    --------
    >>> @provider
    >>> def provides_int() -> int:
    ...     return 42
    """
    return_hint = get_type_hints(func).get("return")
    if return_hint is None:
        warnings.warn(f"{func} has no return type hint. Cannot be a processor.")
    else:
        set_providers({return_hint: func})
    return func


@overload
def get_provider(type_: Type[T]) -> Union[Callable[[], T], None]:
    ...


@overload
def get_provider(type_: object) -> Union[Callable[[], Optional[T]], None]:
    # `object` captures passing get_provider(Optional[type])
    ...


def get_provider(
    type_: Union[object, Type[T]]
) -> Union[Callable[[], T], Callable[[], Optional[T]], None]:
    """Return object provider function given a type.

    An object provider is a function that returns an instance of a
    particular object type.

    This is a form of dependency injection, and, along with
    `inject_dependencies`, allows us to inject objects into functions based on
    type hints.
    """
    return _get_provider(type_, pop=False)


def _get_provider(
    type_: Union[object, Type[T]], pop: bool = False
) -> Union[Callable[[], T], Callable[[], Optional[T]], None]:
    return _STORE._get(type_, provider=True, pop=pop)


@overload
def clear_provider(type_: Type[T]) -> Union[Callable[[], T], None]:
    ...


@overload
def clear_provider(type_: object) -> Union[Callable[[], Optional[T]], None]:
    ...


def clear_provider(
    type_: Union[object, Type[T]], warn_missing: bool = False
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

    Returns
    -------
    Optional[Callable[[], T]]
        The provider function that was cleared, if any.
    """
    result = _get_provider(type_, pop=True)

    if result is None and warn_missing:
        warnings.warn(
            f"No provider was registered for {type_}, and warn_missing is True."
        )
    return result


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

    Raises
    ------
    ValueError
        if clobber is `False` and one of the keys in `mapping` is already
        registered.
    """

    def __init__(
        self,
        mapping: Dict[Type[T], Union[T, Callable[[], T]]],
        clobber: bool = False,
    ) -> None:
        self._before = _STORE._set(mapping, provider=True, clobber=clobber)

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: Any) -> None:

        for (type_, optional), val in self._before.items():
            MAP: dict = _STORE.opt_providers if optional else _STORE.providers
            if val is _STORE._NULL:
                del MAP[type_]
            else:
                MAP[type_] = cast(Callable, val)
