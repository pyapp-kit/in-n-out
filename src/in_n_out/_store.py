from collections import ChainMap
from typing import (
    Any,
    Callable,
    Dict,
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


class Store:
    """A Store is a collection of providers and processors."""

    _NULL = object()
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
        self.providers: Dict[Type, Callable[[], Any]] = {}
        self.opt_providers: Dict[Type, Callable[[], Optional[Any]]] = {}
        self.processors: Dict[Any, Callable[[Any], Any]] = {}
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
    def namespace(self) -> dict[str, object]:
        """Return namespace for type resolution, if this store has one.

        If no namespace is set, this will return an empty `dict`.
        """
        if self._namespace is None:
            return {}
        if callable(self._namespace):
            return dict(self._namespace())
        return dict(self._namespace)

    @namespace.setter
    def namespace(self, ns: Union[Namespace, Callable[[], Namespace]]):
        self._namespace = ns

    def _get(
        self, type_: Union[object, Type[T]], provider: bool, pop: bool
    ) -> Optional[Callable]:
        type_, is_optional = _check_optional(type_)

        # when retrieving a provider, we differentiate between optional and non-optional
        # when trying to retrieve a processor, we don't, because we won't pass a value
        # of `None` to a processor
        if provider:
            _opt: Dict[Any, Callable] = self.opt_providers
            _non_opt: Dict[Any, Callable] = self.providers
            _map: Mapping[Type, Callable]
            _map = ChainMap(_non_opt, _opt) if is_optional else _non_opt
        else:
            _opt = self.processors
            _non_opt = self.processors
            _map = self.processors

        if pop:
            # if we're popping `int`, we should also get rid of `Optional[int]`
            opt_p = _opt.pop(type_, None)
            if is_optional:
                # if we're popping `Optional[int]`, we should not get rid of `int`
                return opt_p
            return _non_opt.pop(type_, None) or opt_p

        if type_ in _map:
            return _map[type_]

        if isinstance(type_, type):
            for key, val in _map.items():
                if issubclass(type_, key):
                    return val
        return None

    def _set(
        self,
        mapping: Mapping[Type[T], Union[T, Callable]],
        provider: bool,
        clobber: bool,
    ) -> dict:
        map_type = "provider" if provider else "processor"
        _before: Dict[Tuple[Type, bool], Any] = {}
        _non_optional = {}
        _optionals = {}

        for type_, obj in mapping.items():
            origin, Toptional = _check_optional(type_)

            _map: Dict[Any, Callable]
            if provider:
                _map = self.opt_providers if Toptional else self.providers
            else:
                _map = self.processors

            if origin in _map and not clobber:
                raise ValueError(
                    f"Type {type_} already has a {map_type} and clobber is False"
                )
            # if provider is not a function, create a function that returns it
            caller = obj if callable(obj) else (lambda: cast(T, obj))

            # get current value
            _before[(origin, Toptional)] = _map.get(origin, self._NULL)

            if Toptional and provider:
                _optionals[origin] = cast(Callable, caller)
            else:
                _non_optional[origin] = cast(Callable, caller)

        if provider:
            self.providers.update(_non_optional)
            self.opt_providers.update(_optionals)
        else:
            self.processors.update(_non_optional)

        return _before


Store._instances[_GLOBAL] = Store(_GLOBAL)
