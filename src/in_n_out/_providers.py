import warnings
from typing import (
    Any,
    Callable,
    ChainMap,
    Dict,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

T = TypeVar("T")
C = TypeVar("C", bound=Callable[[], Any])
_NULL = object()


# registry of Type -> "provider function"
# where each value is a function that is capable
# of retrieving an instance of its corresponding key type.
_PROVIDERS: Dict[Type, Callable[[], Any]] = {}
_OPTIONAL_PROVIDERS: Dict[Type, Callable[[], Optional[Any]]] = {}


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
    if return_hint is not None:
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
    type_, is_optional = _check_optional(type_)

    if pop:
        # if we're popping `int`, we should also get rid of `Optional[int]`
        opt_p = _OPTIONAL_PROVIDERS.pop(type_, None)
        if is_optional:
            # if we're popping `Optional[int]`, we should not get rid of `int`
            return opt_p
        return _PROVIDERS.pop(type_, None)

    _map: Mapping[Type, Union[Callable[[], T], Callable[[], Optional[T]]]]
    _map = ChainMap(_PROVIDERS, _OPTIONAL_PROVIDERS) if is_optional else _PROVIDERS

    if type_ in _map:
        return _map[type_]

    if isinstance(type_, type):
        for key, val in _map.items():
            if issubclass(type_, key):
                return val
    return None


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
        self._before: Dict[Tuple[Type, bool], Any] = {}
        _non_optional: Dict[Type[T], Callable[[], T]] = {}
        _optionals: Dict[Type[T], Callable[[], T]] = {}
        for type_, provider in mapping.items():
            if type_ in _PROVIDERS and not clobber:
                raise ValueError(
                    f"Type {type_} already has a provider and clobber is False"
                )
            # if provider is not a function, create a function that returns it
            pcall = provider if callable(provider) else (lambda: cast(T, provider))
            # check if this is an optional type
            type_, optional = _check_optional(type_)
            self._before[(type_, optional)] = _PROVIDERS.get(type_, _NULL)
            if optional:
                _optionals[type_] = pcall
            else:
                _non_optional[type_] = pcall

        _PROVIDERS.update(_non_optional)
        _OPTIONAL_PROVIDERS.update(_optionals)

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: Any) -> None:
        for (type_, optional), val in self._before.items():
            MAP: dict = _OPTIONAL_PROVIDERS if optional else _PROVIDERS
            if val is _NULL:
                del MAP[type_]
            else:
                MAP[type_] = cast(Callable, val)


def _check_optional(type_: Any) -> Tuple[Type, bool]:
    optional = False
    if get_origin(type_) is Union:
        args = get_args(type_)
        if args and len(args) == 2 and type(None) in args:
            type_ = next(a for a in args if a is not type(None))  # noqa
            optional = True
    return type_, optional
