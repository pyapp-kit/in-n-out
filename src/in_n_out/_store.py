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
    Tuple,
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
Provider = Callable[[], Any]
Processor = Callable[[Any], Any]
Disposer = Callable[[], None]

_GLOBAL = "global"

Namespace = Mapping[str, object]

HintArg = object
Weight = float
ProviderProcessorIterable = Iterable[
    Union[Tuple[HintArg, Callable], Tuple[HintArg, Callable, Weight]]
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
        provider: Provider,
        weight: float = 0,
    ) -> Disposer:
        """Register `provider` as a provider of `type_hint`.

        Parameters
        ----------
        type_hint : object
            A type or type hint that `provider` provides.
        provider : Callable
            A provider callback. Must be able to accept no arguments.
        weight : float, optional
            A weight with which to sort this provider. Higher weights are given
            priority, by default 0

        Returns
        -------
        Callable
            A function that unregisters the provider.
        """
        return self.register_providers([(type_hint, provider, weight)])

    def register_providers(
        self,
        providers: Union[Mapping[object, Callable], ProviderProcessorIterable],
    ) -> Disposer:
        """Register multiple providers at once.

        Parameters
        ----------
        providers : Union[Mapping[object, Callable], ProviderProcessorIterable]
            Either a mapping of {type_hint: provider} pairs, or an iterable of
            (type_hint, provider) or (type_hint, provider, weight) tuples.

        Returns
        -------
        Callable
            A function that unregisters the provider.
        """
        return self._register_callbacks(providers, True)

    def iter_providers(
        self, hint: Union[object, Type[T]]
    ) -> Iterable[Callable[[], Optional[T]]]:
        """Iterate over all providers of `hint`.

        Parameters
        ----------
        hint : Union[object, Type[T]]
            A type or type hint for which to return providers.

        Yields
        ------
        Iterable[Callable[[], Optional[T]]]
            Iterable of provider callbacks.
        """
        th = TypeHint(_check_optional(hint)[0])
        for hint, providers in self._cached_provider_map.items():
            if th.is_subtype(hint):
                yield from providers

    def provide(self, hint: Union[object, Type[T]]) -> Optional[T]:
        """Provide an instance of `hint`.

        This will iterate over all providers of `hint` and return the first
        one that returns a non-`None` value.

        Parameters
        ----------
        hint : Union[object, Type[T]]
            A type or type hint for which to return a value

        Returns
        -------
        Optional[T]
            The first non-`None` value returned by a provider, or `None` if no
            providers return a value.
        """
        for provider in self.iter_providers(hint):
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
        """Decorate `func` as a provider of its first parameter type.

        Note, If func returns `Optional[Type]`, it will be registered as a provider
        for Type.

        Parameters
        ----------
        func : Optional[Provider]
            A function to decorate. If not provided, a decorator is returned.
        weight : float
            A weight with which to sort this provider. Higher weights are given
            priority, by default 0
        for_type : Optional[object]
            Optional type or type hint for which to register this provider. If not
            provided, the return annotation of `func` will be used.

        Returns
        -------
        Union[Callable[[Provider], Provider], Provider]
            If `func` is not provided, a decorator is returned, if `func` is provided
            then the function is returned..

        Examples
        --------
        >>> @store.provider
        >>> def provide_int() -> int:
        ...     return 42
        """

        def _deco(func: Provider, hint: Optional[object] = for_type) -> Provider:
            if hint is None:
                hint = resolve_type_hints(func, localns=self.namespace).get("return")
            if hint is None:
                warnings.warn(f"{func} has no return type hint. Cannot be a provider.")
            else:
                self.register_provider(type_hint=hint, provider=func, weight=weight)
            return func

        return _deco(func) if func is not None else _deco

    # -----------------------

    def register_processor(
        self,
        type_hint: object,
        processor: Processor,
        weight: float = 0,
    ) -> Disposer:
        """Register `processor` as a processor of `type_hint`.

        Parameters
        ----------
        type_hint : object
            A type or type hint that `processor` can handle.
        processor : Callable
            A processor callback. Must accept at least one argument.
        weight : float, optional
            A weight with which to sort this processor. Higher weights are given
            priority, by default 0.  When invoking processors, all processors
            will be invoked in descending weight order, unless `first_processor_only`
            is set to `True`.

        Returns
        -------
        Callable
            A function that unregisters the processor.
        """
        return self.register_processors([(type_hint, processor, weight)])

    def register_processors(
        self,
        processors: Union[Mapping[object, Processor], ProviderProcessorIterable],
    ) -> Disposer:
        """Register multiple processors at once.

        Parameters
        ----------
        processors : Union[Mapping[object, Callable], ProviderProcessorIterable]
            Either a mapping of {type_hint: processor} pairs, or an iterable of
            (type_hint, processor) or (type_hint, processor, weight) tuples.

        Returns
        -------
        Callable
            A function that unregisters the provider.
        """
        return self._register_callbacks(processors, False)

    def iter_processors(
        self, hint: Union[object, Type[T]]
    ) -> Iterable[Callable[[T], Any]]:
        """Iterate over all processors of `hint`.

        Parameters
        ----------
        hint : Union[object, Type[T]]
            A type or type hint for which to return processors.

        Yields
        ------
        Iterable[Callable[[], Optional[T]]]
            Iterable of processor callbacks.
        """
        th = TypeHint(_check_optional(hint)[0])
        for _hint, processor in self._cached_processor_map.items():
            if th.is_subtype(_hint):
                yield from processor

    def process(
        self,
        hint: Union[object, Type[T]],
        result: Any,
        first_processor_only: bool = False,
        raise_exception: bool = False,
    ) -> None:
        """Provide an instance of `type_`.

        This will iterate over all providers of `type_` and return the first
        one that returns a non-`None` value.

        Parameters
        ----------
        hint : object
            A type or type hint for which to return a value
        result : Any
            The result to process
        first_processor_only : bool, optional
            If `True`, only the first processor will be invoked, otherwise all
            processors will be invoked, in descending weight order.
        raise_exception : bool, optional
            If `True`, and a processor raises an exception, it will be raised
            and the remaining processors will not be invoked.
        """
        for processor in self.iter_processors(hint):  # type: ignore
            try:
                processor(result)
            except Exception as e:  # pragma: no cover
                if raise_exception:
                    raise e
                warnings.warn(
                    f"Processor {processor!r} failed to process result {result!r}: {e}"
                )
            if first_processor_only:
                break

    @overload
    def processor(
        self,
        func: Processor,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Processor:
        ...

    @overload
    def processor(
        self,
        func: Literal[None] = ...,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Callable[[Processor], Processor]:
        ...

    def processor(
        self,
        func: Optional[Processor] = None,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Union[Callable[[Processor], Processor], Processor]:
        """Decorate `func` as a processor of its first parameter type.

        Parameters
        ----------
        func : Optional[Processor], optional
            A function to decorate. If not provided, a decorator is returned.
        weight : float, optional
            A weight with which to sort this processor. Higher weights are given
            priority, by default 0.  When invoking processors, all processors
            will be invoked in descending weight order, unless `first_processor_only`
            is set to `True`.
        for_type : Optional[object]
            Optional type or type hint that this processor can handle. If not
            provided, the type hint of the first parameter of `func` will be used.

        Returns
        -------
        Union[Callable[[Processor], Processor], Processor]
            If `func` is not provided, a decorator is returned, if `func` is provided
            then the function is returned.

        Examples
        --------
        >>> @store.processor
        >>> def process_int(x: int) -> None:
        ...     print("Processing int:", x)
        """

        def _deco(func: Processor, hint: Optional[object] = for_type) -> Processor:
            if hint is None:
                hints = resolve_type_hints(func, localns=self.namespace)
                hints.pop("return", None)
                if hints:
                    hint = list(hints.values())[0]

            if hint is None:
                warnings.warn(
                    f"{func} has no argument type hints. Cannot be a processor."
                )
            else:
                self.register_processor(type_hint=hint, processor=func, weight=weight)
            return func

        return _deco(func) if func is not None else _deco

    # -----------------

    @cached_property
    def _cached_provider_map(self) -> Dict[TypeHint, List[Provider]]:
        return self._build_map(self._providers)

    @cached_property
    def _cached_processor_map(self) -> Dict[TypeHint, List[Processor]]:
        return self._build_map(self._processors)

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
    ) -> Disposer:

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
