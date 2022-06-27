from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

T = TypeVar("T")
C = TypeVar("C", bound=Callable)
_NULL = object()


# registry of Type -> "provider function"
# where each value is a function that is capable
# of retrieving an instance of its corresponding key type.
_PROVIDERS: Dict[Type, Callable[..., Optional[object]]] = {}
Provider = Callable[..., Optional[T]]


def provider(func: C) -> C:
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
    if get_origin(return_hint) == Union:
        if (args := get_args(return_hint)) and len(args) == 2 and type(None) in args:
            return_hint = next(a for a in args if a is not type(None))  # noqa
    if return_hint is not None:
        _PROVIDERS[return_hint] = func
    return func


def get_provider(type_: Union[Any, Type[T]]) -> Optional[Provider]:
    """Return object provider function given a type.

    An object provider is a function that returns an instance of a
    particular object type.

    This is a form of dependency injection, and, along with
    `inject_dependencies`, allows us to inject objects into functions based on
    type hints.
    """
    if type_ in _PROVIDERS:
        return cast(Provider, _PROVIDERS[type_])

    if isinstance(type_, type):
        for key, val in _PROVIDERS.items():
            if issubclass(type_, key):
                return cast(Provider, val)
    return None


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
        self, mapping: Dict[Type[T], Callable[..., Optional[T]]], clobber: bool = False
    ) -> None:
        self._before = {}
        for k in mapping:
            if k in _PROVIDERS and not clobber:
                raise ValueError(
                    f"Class {k} already has a provider and clobber is False"
                )
            self._before[k] = _PROVIDERS.get(k, _NULL)
        _PROVIDERS.update(mapping)

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: Any) -> None:
        for key, val in self._before.items():
            if val is _NULL:
                del _PROVIDERS[key]
            else:
                _PROVIDERS[key] = val  # type: ignore
