from collections import ChainMap
from inspect import CO_VARARGS
from types import CodeType
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from ._util import _check_optional

T = TypeVar("T")
Provider = TypeVar("Provider", bound=Callable[[], Any])
Processor = TypeVar("Processor", bound=Callable[[Any], Any])
_GLOBAL = "global"

Namespace = Mapping[str, object]


class _NullSentinel:
    ...


class Store(Generic[T]):
    """A Store is a collection of providers and processors."""

    _NULL = _NullSentinel()
    _instances: Dict[str, "Store"] = {}

    @classmethod
    def create(cls, name: str) -> "Store":
        """Create a new Store instance with the given `name`.

        This name can be used to refer to the Store in other functions.

        Parameters
        ----------
        name : str
            A name for the Store.

        Returns
        -------
        Store
            A Store instance with the given `name`.

        Raises
        ------
        KeyError
            If the name is already in use, or the name is 'global'.
        """
        name = name.lower()
        if name == _GLOBAL:
            raise KeyError("'global' is a reserved store name")
        elif name in cls._instances:
            raise KeyError(f"Store {name!r} already exists")
        cls._instances[name] = cls(name)
        return cls._instances[name]

    @classmethod
    def get_store(cls, name: Optional[str] = None) -> "Store":
        """Get a Store instance with the given `name`.

        Parameters
        ----------
        name : str
            The name of the Store.

        Returns
        -------
        Store
            A Store instance with the given `name`.

        Raises
        ------
        KeyError
            If the name is not in use.
        """
        name = (name or _GLOBAL).lower()
        if name not in cls._instances:
            raise KeyError(f"Store {name!r} does not exist")
        return cls._instances[name]

    @classmethod
    def destroy(cls, name: str) -> None:
        """Destroy Store instance with the given `name`."""
        name = name.lower()
        if name == _GLOBAL:
            raise ValueError("The global store cannot be destroyed")
        elif name not in cls._instances:
            raise KeyError(f"Store {name!r} does not exist")
        del cls._instances[name]

    def __init__(self, name: str) -> None:
        self._name = name
        self.providers: Dict[Type[T], Callable[[], T]] = {}
        self.opt_providers: Dict[Type[T], Callable[[], Optional[T]]] = {}
        self.processors: Dict[Type[T], Callable[[T], Any]] = {}
        self._namespace: Union[Namespace, Callable[[], Namespace], None] = None

    @property
    def name(self) -> str:
        """Return the name of this Store."""
        return self._name

    def clear(self) -> None:
        """Clear all providers and processors."""
        self.providers.clear()
        self.opt_providers.clear()
        self.processors.clear()

    @property
    def namespace(self) -> Dict[str, object]:
        """Return namespace for type resolution, if this store has one.

        If no namespace is set, this will return an empty `dict`.
        """
        if self._namespace is None:
            return {}
        if callable(self._namespace):
            return dict(self._namespace())
        return dict(self._namespace)

    @namespace.setter
    def namespace(self, ns: Union[Namespace, Callable[[], Namespace]]) -> None:
        self._namespace = ns

    def _pop_processor(
        self, type_: Union[object, Type[T]]
    ) -> Optional[Callable[[T], Any]]:
        type_, _ = _check_optional(type_)
        return self.processors.pop(type_, None)

    def _get_processor(
        self, type_: Union[object, Type[T]]
    ) -> Optional[Callable[[T], Any]]:
        type_, _ = _check_optional(type_)
        if type_ in self.processors:
            return self.processors[type_]

        if isinstance(type_, type):
            for key, val in self.processors.items():
                if issubclass(type_, key):
                    return val
        return None

    def _pop_provider(
        self, type_: Union[object, Type[T]]
    ) -> Optional[Callable[[], Optional[T]]]:
        type_, is_optional = _check_optional(type_)

        # if we're popping `int`, we should also get rid of `Optional[int]`
        opt_p = self.opt_providers.pop(type_, None)
        if is_optional:
            # if we're popping `Optional[int]`, we should not get rid of `int`
            return opt_p
        return self.providers.pop(type_, None) or opt_p

    def _get_provider(self, type_: Union[object, Type[T]]) -> Optional[Callable[[], T]]:
        type_, is_optional = _check_optional(type_)

        # when retrieving a provider, we differentiate between optional and non-optional
        # when trying to retrieve a processor, we don't, because we won't pass a value
        # of `None` to a processor
        _opt: Dict[Any, Callable] = self.opt_providers
        _non_opt: Dict[Any, Callable] = self.providers
        _map: Mapping[Type, Callable]
        _map = ChainMap(_non_opt, _opt) if is_optional else _non_opt

        if type_ in _map:
            return _map[type_]

        if isinstance(type_, type):
            for key, val in _map.items():
                if issubclass(type_, key):
                    return val
        return None

    def _set_processor(
        self,
        mapping: Mapping[Union[Type[T], object], Callable[[T], Any]],
        clobber: bool,
    ) -> Dict[Type[T], Union[_NullSentinel, Callable[[T], Any]]]:
        _before: Dict[Type[T], Union[_NullSentinel, Callable[[T], Any]]] = {}
        _validated: Dict[Type[T], Callable[[T], Any]] = {}

        for type_, obj in mapping.items():
            origin, _ = _check_optional(type_)

            if origin in self.processors and not clobber:
                raise ValueError(
                    f"Type {type_} already has a processor and 'clobber' is False"
                )

            # get current value
            _before[origin] = self.processors.get(origin, self._NULL)
            _validated[origin] = _validate_processor(obj)

        self.processors.update(_validated)

        return _before

    def _set_provider(
        self,
        mapping: Mapping[Union[Type[T], object], Union[T, Callable]],
        clobber: bool,
    ) -> Dict[Tuple[Type, bool], Union[_NullSentinel, Callable[[], T]]]:

        _before: Dict[Tuple[Type, bool], Union[_NullSentinel, Callable[[], T]]] = {}
        _non_optional = {}
        _optionals = {}

        for type_, obj in mapping.items():
            origin, type_optional = _check_optional(type_)

            if type_optional:  # sourcery skip: assign-if-exp
                _map: Dict[Type[T], Callable] = self.opt_providers
            else:
                _map = self.providers
            if origin in _map and not clobber:
                raise ValueError(
                    f"Type {type_} already has a provider and 'clobber' is False"
                )
            # if provider is not a function, create a function that returns it
            caller: Callable = _validate_provider(obj)

            # get current value
            _before[(origin, type_optional)] = _map.get(origin, self._NULL)

            if type_optional:
                _optionals[origin] = caller
            else:
                _non_optional[origin] = caller

        self.providers.update(_non_optional)
        self.opt_providers.update(_optionals)

        return _before


Store._instances[_GLOBAL] = Store(_GLOBAL)


def _validate_provider(obj: Union[T, Callable[[], T]]) -> Callable[[], T]:
    """Check that an object is a valid provider.

    Can either be a function or an object. If a non-callable is passed, a function
    that returns it is created.
    """
    return obj if callable(obj) else (lambda: cast(T, obj))


def _validate_processor(obj: Callable[[T], Any]) -> Callable[[T], Any]:
    """Validate a processor.

    Processors must be a callable that accepts at least one argument(excluding
    keyword-only arguments).
    """
    if not callable(obj):
        raise ValueError(f"Processors must be callable. Got {obj!r}")
    co: Optional[CodeType] = getattr(obj, "__code__", None)
    if not co:
        # if we don't have a code object, we can't check the number of arguments
        # TODO: see if we can do better in the future, but better to just return
        # the callable for now.
        return obj
    if co.co_argcount < 1 and not (co.co_flags & CO_VARARGS):
        name = getattr(obj, "__name__", None) or obj
        raise ValueError(
            f"Processors must take at least one argument. {name!r} takes none."
        )
    return obj
