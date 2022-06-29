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


class _Store:
    _NULL = object()

    def __init__(self) -> None:
        self.providers: Dict[Type, Callable[[], Any]] = {}
        self.opt_providers: Dict[Type, Callable[[], Optional[Any]]] = {}
        self.processors: Dict[Any, Callable[[Any], Any]] = {}


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
        self,mapping: Mapping[Type[T], Union[T, Callable]], provider: bool, clobber: bool
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

_STORE = _Store()