from __future__ import annotations

import contextlib
import warnings
from functools import cached_property, wraps
from inspect import CO_VARARGS, isgeneratorfunction
from types import CodeType
from typing import (
    TYPE_CHECKING,
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

from ._type_resolution import _resolve_sig_or_inform, resolve_type_hints
from ._util import _split_union, issubclassable

T = TypeVar("T")
Provider = Callable[[], Any]
ProviderVar = TypeVar("ProviderVar", bound=Provider)

Processor = Callable[[Any], Any]
ProcessorVar = TypeVar("ProcessorVar", bound=Processor)

Disposer = Callable[[], None]

_GLOBAL = "global"

Namespace = Mapping[str, object]

HintArg = object
Weight = float
ProviderProcessorIterable = Iterable[
    Union[Tuple[HintArg, Callable], Tuple[HintArg, Callable, Weight]]
]

if TYPE_CHECKING:
    from inspect import Signature

    from typing_extensions import ParamSpec

    from ._type_resolution import RaiseWarnReturnIgnore

    P = ParamSpec("P")
    R = TypeVar("R")


class _NullSentinel:
    ...


class _RegisteredCallback(NamedTuple):
    origin: type
    callback: Callable
    hint_optional: bool
    weight: float


class Store:
    """A Store is a collection of providers and processors."""

    _NULL = _NullSentinel()
    _instances: Dict[str, Store] = {}

    @classmethod
    def create(cls, name: str) -> Store:
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
    def get_store(cls, name: Optional[str] = None) -> Store:
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
        self.on_unresolved_required_args: RaiseWarnReturnIgnore = "raise"
        self.on_unannotated_required_args: RaiseWarnReturnIgnore = "warn"

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
        return self._iter_type_map(hint, self._cached_provider_map)

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
        func: ProviderVar,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> ProviderVar:
        ...

    @overload
    def provider(
        self,
        func: Literal[None] = ...,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Callable[[ProviderVar], ProviderVar]:
        ...

    def provider(
        self,
        func: Optional[ProviderVar] = None,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Union[Callable[[ProviderVar], ProviderVar], ProviderVar]:
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

        def _deco(func: ProviderVar, hint: Optional[object] = for_type) -> ProviderVar:
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
        return self._iter_type_map(hint, self._cached_processor_map)

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
        func: ProcessorVar,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> ProcessorVar:
        ...

    @overload
    def processor(
        self,
        func: Literal[None] = ...,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Callable[[ProcessorVar], ProcessorVar]:
        ...

    def processor(
        self,
        func: Optional[ProcessorVar] = None,
        *,
        weight: float = 0,
        for_type: Optional[object] = None,
    ) -> Union[Callable[[ProcessorVar], ProcessorVar], ProcessorVar]:
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

        def _deco(
            func: ProcessorVar, hint: Optional[object] = for_type
        ) -> ProcessorVar:
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

    # ------------------------------------------------------------------------------

    @overload
    def inject_dependencies(
        self,
        func: Callable[P, R],
        *,
        localns: Optional[dict] = None,
        on_unresolved_required_args: Optional[RaiseWarnReturnIgnore] = None,
        on_unannotated_required_args: Optional[RaiseWarnReturnIgnore] = None,
    ) -> Callable[P, R]:
        ...

    @overload
    def inject_dependencies(
        self,
        func: Literal[None] = None,
        *,
        localns: Optional[dict] = None,
        on_unresolved_required_args: Optional[RaiseWarnReturnIgnore] = None,
        on_unannotated_required_args: Optional[RaiseWarnReturnIgnore] = None,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        ...

    def inject_dependencies(
        self,
        func: Optional[Callable[P, R]] = None,
        *,
        localns: Optional[dict] = None,
        on_unresolved_required_args: Optional[RaiseWarnReturnIgnore] = None,
        on_unannotated_required_args: Optional[RaiseWarnReturnIgnore] = None,
    ) -> Union[Callable[P, R], Callable[[Callable[P, R]], Callable[P, R]]]:
        """Decorator returns func that can access/process objects based on type hints.

        This is form of dependency injection, and result processing.  It does 2 things:

        1. If `func` includes a parameter that has a type with a registered provider
        (e.g. `Viewer`, or `Layer`), then this decorator will return a new version of
        the input function that can be called *without* that particular parameter.

        2. If `func` has a return type with a registered processor (e.g. `ImageData`),
        then this decorator will return a new version of the input function that, when
        called, will have the result automatically processed by the current processor
        for that type (e.g. in the case of `ImageData`, it will be added to the viewer.)

        Parameters
        ----------
        func : Callable[P, R]
            a function with type hints
        localns : Optional[dict]
            Optional local namespace for name resolution, by default None
        on_unresolved_required_args : RaiseWarnReturnIgnore
            What to do when a required parameter (one without a default) is encountered
            with an unresolvable type annotation.
            Must be one of the following (by default 'raise'):

                - 'raise': immediately raise an exception
                - 'warn': warn and return the original function
                - 'return': return the original function without warning
                - 'ignore': currently an alias for `return`, but will be used in
                the future to allow the decorator to proceed.

        on_unannotated_required_args : RaiseWarnReturnIgnore
            What to do when a required parameter (one without a default) is encountered
            with an *no* type annotation. These functions are likely to fail when called
            later if the required parameter is not provided.
            Must be one of the following (by default 'warn'):

                - 'raise': immediately raise an exception
                - 'warn': warn, but continue decorating
                - 'return': immediately return the original function without warning
                - 'ignore': continue decorating without warning.

        Returns
        -------
        Callable
            A function with dependencies injected
        """
        on_unres = on_unresolved_required_args or self.on_unresolved_required_args
        on_unann = on_unannotated_required_args or self.on_unannotated_required_args

        # inner decorator, allows for optional decorator arguments
        def _inner(func: Callable[P, R]) -> Callable[P, R]:
            # if the function takes no arguments and has no return annotation
            # there's nothing to be done
            code: Optional[CodeType] = getattr(func, "__code__", None)
            if (code and not code.co_argcount) and "return" not in getattr(
                func, "__annotations__", {}
            ):
                return func

            # get a signature object with all type annotations resolved
            # this may result in a NameError if a required argument is unresolveable.
            # There may also be unannotated required arguments, which will likely fail
            # when the function is called later. We break this out into a seperate
            # function to handle notifying the user on these cases.
            sig = _resolve_sig_or_inform(
                func,
                localns={**self.namespace, **(localns or {})},
                on_unresolved_required_args=on_unres,
                on_unannotated_required_args=on_unann,
            )
            if sig is None:  # something went wrong, and the user was notified.
                return func
            process_result = sig.return_annotation is not sig.empty

            # get provider functions for each required parameter
            @wraps(func)
            def _exec(*args: P.args, **kwargs: P.kwargs) -> R:
                # sourcery skip: use-named-expression
                # we're actually calling the "injected function" now

                _sig = cast("Signature", sig)
                # first, get and call the provider functions for each parameter type:
                _kwargs: Dict[str, Any] = {}
                for param in _sig.parameters.values():
                    provided = self.provide(param.annotation)
                    if provided is not None:
                        _kwargs[param.name] = provided

                # use bind_partial to allow the caller to still provide their own args
                # if desired. (i.e. the injected deps are only used if not provided)
                bound = _sig.bind_partial(*args, **kwargs)
                bound.apply_defaults()
                _kwargs.update(**bound.arguments)

                try:  # call the function with injected values
                    result = func(**_kwargs)
                except TypeError as e:
                    # likely a required argument is still missing.
                    raise TypeError(
                        f"After injecting dependencies for arguments {set(_kwargs)}, "
                        f"{e}"
                    ) from e

                if result is not None and process_result:
                    # TODO: pass on keywords
                    self.process(_sig.return_annotation, result)

                return result

            out = _exec

            # if it came in as a generatorfunction, it needs to go out as one.
            if isgeneratorfunction(func):

                @wraps(func)
                def _gexec(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore
                    yield from _exec(*args, **kwargs)  # type: ignore

                out = _gexec

            # update some metadata on the decorated function.
            out.__signature__ = sig  # type: ignore [attr-defined]
            out.__annotations__ = {
                **{p.name: p.annotation for p in sig.parameters.values()},
                "return": sig.return_annotation,
            }
            out.__doc__ = (
                out.__doc__ or ""
            ) + "\n\n*This function will inject dependencies when called.*"
            return out

        return _inner(func) if func is not None else _inner

    # -----------------

    @cached_property
    def _cached_provider_map(self) -> Dict[type, List[Provider]]:
        return self._build_map(self._providers)

    @cached_property
    def _cached_processor_map(self) -> Dict[type, List[Processor]]:
        return self._build_map(self._processors)

    def _build_map(
        self, registry: List[_RegisteredCallback]
    ) -> Dict[type, List[Callable]]:
        """Build a map of type hints to callbacks.

        This is the sorted and cached version of the map that will be used to resolve
        a provider or processor.
        """
        out: Dict[type, List[_RegisteredCallback]] = {}
        for p in registry:
            if p.origin not in out:
                out[p.origin] = []
            out[p.origin].append(p)

        return {
            hint: [v.callback for v in sorted(val, key=self._sort_key, reverse=True)]
            for hint, val in out.items()
        }

    def _iter_type_map(
        self, hint: Union[object, Type[T]], callback_map: Mapping[type, List[Callable]]
    ) -> Iterable[Callable]:
        for origin in _split_union(hint)[0]:
            if origin in callback_map:
                yield from callback_map[origin]
                return

            for _hint, processor in callback_map.items():
                if issubclass(origin, _hint):
                    yield from processor
                    return

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
            origins, is_optional = _split_union(type_)
            for origin in origins:
                if not issubclassable(origin):
                    regname = "provider" if providers else "processor"
                    raise TypeError(
                        f"{type_!r} cannot be used as a {regname} hint, since it "
                        "cannot be used as the second argument of `issubclass`"
                    )
                _p.append(
                    _RegisteredCallback(
                        origin=origin,
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
