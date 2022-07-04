import contextlib
import warnings
from functools import cached_property
from inspect import CO_VARARGS
from types import CodeType
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from beartype.math import TypeHint

from ._type_resolution import resolve_type_hints
from ._util import _check_optional

T = TypeVar("T")
Provider = TypeVar("Provider", bound=Callable[[], Any])
Processor = TypeVar("Processor", bound=Callable[[Any], Any])
_GLOBAL = "global"

Namespace = Mapping[str, object]

HintArg = object
Weight = float
ProviderProcessorIterable = Iterable[
    Union[tuple[HintArg, Callable], tuple[HintArg, Callable, Weight]]
]


class _NullSentinel:
    ...


class _RegisteredCallback(NamedTuple):
    hint: TypeHint
    callback: Callable
    hint_optional: bool
    weight: float


class Store:
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
        self._providers: List[_RegisteredCallback] = []
        self._processors: List[_RegisteredCallback] = []
        self._namespace: Union[Namespace, Callable[[], Namespace], None] = None

    @property
    def name(self) -> str:
        """Return the name of this Store."""
        return self._name

    def clear(self) -> None:
        """Clear all providers and processors."""
        self._providers.clear()
        self._processors.clear()
        with contextlib.suppress(AttributeError):
            del self._cached_processor_map
        with contextlib.suppress(AttributeError):
            del self._cached_provider_map

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

    def register_provider(
        self,
        type_hint: object,
        provider: Callable,
        weight: float = 0,
    ) -> Callable:
        return self.register_providers([(type_hint, provider, weight)])

    def register_providers(
        self,
        providers: Union[Mapping[object, Callable], ProviderProcessorIterable],
    ) -> Callable:
        return self._register_callbacks(providers, True)

    @cached_property
    def _cached_provider_map(self) -> Dict[TypeHint, List[Callable]]:
        return self._build_map(self._providers)

    def iter_providers(
        self, type_: Union[object, Type[T]]
    ) -> Iterable[Callable[[], Optional[T]]]:
        th = TypeHint(_check_optional(type_)[0])
        for hint, providers in self._cached_provider_map.items():
            if th.is_subtype(hint):
                yield from providers

    def provide(self, type_: Union[object, Type[T]]) -> Optional[T]:
        for provider in self.iter_providers(type_):
            result = provider()
            if result is not None:
                return result
        return None

    @overload
    def provider(
        self,
        func: Provider,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Provider:
        ...

    @overload
    def provider(
        self,
        func: Literal[None] = ...,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Callable[[Provider], Provider]:
        ...

    def provider(
        self,
        func: Optional[Provider] = None,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Union[Callable[[Provider], Provider], Provider]:
        def _deco(func: Provider, hint: Optional[object] = for_type) -> Provider:
            if hint is None:
                hint = resolve_type_hints(func, localns=self.namespace).get("return")
            if hint is None:
                warnings.warn(f"{func} has no return type hint. Cannot be a provider.")
            else:
                self.register_provider(type_hint=hint, provider=func, weight=weight)
            return func

        return _deco(func) if func is not None else _deco

    def register_processor(
        self,
        type_hint: object,
        processor: Callable,
        weight: float = 0,
    ) -> Callable:
        return self.register_processors([(type_hint, processor, weight)])

    def register_processors(
        self,
        processors: Union[Mapping[object, Callable], ProviderProcessorIterable],
    ) -> Callable:
        return self._register_callbacks(processors, False)

    @cached_property
    def _cached_processor_map(self) -> Dict[TypeHint, List[Callable[[Any], None]]]:
        return self._build_map(self._processors)

    def iter_processors(self, type_: object) -> Iterable[Callable[[Any], None]]:
        th = TypeHint(_check_optional(type_)[0])
        for hint, processor in self._cached_processor_map.items():
            if th.is_subtype(hint):
                yield from processor

    def process(
        self,
        hint: object,
        result: Any,
        first_processor_only: bool = False,
        raise_exception: bool = False,
    ) -> None:
        for processor in self.iter_processors(hint):
            try:
                processor(result)
            except Exception as e:
                if raise_exception:
                    raise e
                warnings.warn(
                    f"Processor {processor!r} failed to process result {result!r}: {e}"
                )
            if first_processor_only:
                break

    def _build_map(
        self, registry: List[_RegisteredCallback]
    ) -> Dict[TypeHint, List[Callable]]:
        """Build a map of type hints to callbacks.

        This is the sorted and cached version of the map that will be used to resolve
        a provider or processor.
        """
        out: Dict[TypeHint, List[_RegisteredCallback]] = {}
        for p in registry:
            if p.hint not in out:
                out[p.hint] = []
            out[p.hint].append(p)

        return {
            hint: [v.callback for v in sorted(val, key=self._sort_key, reverse=True)]
            for hint, val in out.items()
        }

    def _sort_key(self, p: _RegisteredCallback) -> float:
        """How we sort registered callbacks within the same type hint."""
        return p.weight

    def _register_callbacks(
        self,
        callbacks: Union[Mapping[object, Callable], ProviderProcessorIterable],
        providers: bool = True,
    ) -> Callable[[], None]:

        _p: List[_RegisteredCallback] = []

        if isinstance(callbacks, Mapping):
            callbacks = callbacks.items()

        if providers:
            check: Callable[[Any], Callable] = _validate_provider
        else:
            check = _validate_processor

        for type_, callback, *weight in callbacks:
            origin, is_optional = _check_optional(type_)
            _p.append(
                _RegisteredCallback(
                    hint=TypeHint(origin),
                    callback=check(callback),
                    hint_optional=is_optional,
                    weight=weight[0] if weight else 0,
                )
            )

        reg = self._providers if providers else self._processors

        def _dispose() -> None:
            for p in _p:
                with contextlib.suppress(ValueError):
                    reg.remove(p)
            with contextlib.suppress(AttributeError):
                if providers:
                    del self._cached_provider_map
                else:
                    del self._cached_processor_map

        if _p:
            reg.extend(_p)
            with contextlib.suppress(AttributeError):
                if providers:
                    del self._cached_provider_map
                else:
                    del self._cached_processor_map

        return _dispose


Store._instances[_GLOBAL] = GLOBAL_STORE = Store(_GLOBAL)


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
