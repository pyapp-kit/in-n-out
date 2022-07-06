from __future__ import annotations

import contextlib
import types
import warnings
import weakref
from functools import cached_property, wraps
from inspect import CO_VARARGS, isgeneratorfunction
from types import CodeType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ContextManager,
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

if TYPE_CHECKING:
    from inspect import Signature

    from typing_extensions import ParamSpec

    from ._type_resolution import RaiseWarnReturnIgnore

    P = ParamSpec("P")
    R = TypeVar("R")


T = TypeVar("T")
Provider = Callable[[], Any]  # provider should be able to take no arguments
Processor = Callable[[Any], Any]  # a processor must take one positional arg
PPCallback = Union[Provider, Processor]

# typevars that retain the signatures of the values passed in
ProviderVar = TypeVar("ProviderVar", bound=Provider)
ProcessorVar = TypeVar("ProcessorVar", bound=Processor)

Disposer = Callable[[], None]
Namespace = Mapping[str, object]
HintArg = object
Weight = float

# (callback,)
# (callback, type_hint)
# (callback, type_hint, weight)
CallbackTuple = Union[
    Tuple[PPCallback], Tuple[PPCallback, HintArg], Tuple[PPCallback, HintArg, Weight]
]
# All of the valid argument that can be passed to register()
CallbackIterable = Union[Iterable[CallbackTuple], Mapping[HintArg, PPCallback]]


_GLOBAL = "global"


class _NullSentinel:
    ...


class _RegisteredCallback(NamedTuple):
    origin: type
    callback: Callable
    hint_optional: bool
    weight: float
    subclassable: bool


class _CachedMap(NamedTuple):
    all: Dict[object, List[Union[Processor, Provider]]]
    subclassable: Dict[type, List[Union[Processor, Provider]]]


class InjectionContext(ContextManager):
    """Context manager for registering callbacks.

    Primarily used as `with store.regsiter(...)`.
    """

    def __init__(
        self,
        store: Store,
        *,
        providers: Optional[CallbackIterable] = None,
        processors: Optional[CallbackIterable] = None,
    ) -> None:
        self._disposers = []
        if providers is not None:
            self._disposers.append(store._register_callbacks(providers, True))
        if processors is not None:
            self._disposers.append(store._register_callbacks(processors, False))

    def __exit__(self, *_: Any) -> None:
        self.cleanup()

    def cleanup(self) -> Any:
        """Cleanup any callbacks registered in this context."""
        for dispose in self._disposers:
            dispose()
        self._disposers.clear()


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
        """Destroy Store instance with the given `name`.

        Parameters
        ----------
        name : str
            The name of the Store.

        Raises
        ------
        ValueError
            If the name matches the global store name.
        KeyError
            If the name is not in use.
        """
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

    # ------------------------- Callback registration ------------------------------

    def register(
        self,
        *,
        providers: Optional[CallbackIterable] = None,
        processors: Optional[CallbackIterable] = None,
    ) -> InjectionContext:
        """Register multiple providers and/or processors at once.

        This may be used as a context manager to temporarily register providers and/or
        processors.

        The format for providers/processors is one of:
            - a mapping of {type_hint: provider} pairs
            - an iterable of 1, 2, or 3-tuples, where each tuple in the iterable is:
                -  (callback,)
                -  (callback, type_hint,)
                -  (callback, type_hint, weight)

        Parameters
        ----------
        providers :Optional[CallbackIterable]
            mapping or iterable of providers to register. See format in notes above.
        processors :Optional[CallbackIterable]
            mapping or iterable of processors to register. See format in notes above.

        Returns
        -------
        InjectionContext
            Context manager for unregistering providers and processors. If the context
            is entered with `with store.register(): ...`, then callbacks will be
            unregistered when the context is exited.  Callbacks may also be unregistered
            manually using the `.cleanup()` method of the returned context manager.

        Examples
        --------
        >>> with store.register(
                providers={int: lambda: 42},  # provided as hint->callback map
                processors=[
                    (my_callback),  # hint inferred from signature
                    (my_other_callback, str),  # hint explicitly provided
                    (my_third_callback, int, 10)  # weight explicitly provided
                ],
            ):
                ...
        """
        return InjectionContext(self, providers=providers, processors=processors)

    def register_provider(
        self,
        provider: Provider,
        type_hint: Optional[object] = None,
        weight: float = 0,
    ) -> InjectionContext:
        """Register `provider` as a provider of `type_hint`.

        Parameters
        ----------
        provider : Callable
            A provider callback. Must be able to accept no arguments.
        type_hint : Optional[object]
            A type or type hint that `provider` provides.  If not provided, it will
            be inferred from the return annotation of `provider`.
        weight : float, optional
            A weight with which to sort this provider. Higher weights are given
            priority, by default 0

        Returns
        -------
        Callable
            A function that unregisters the provider.
        """
        return self.register(providers=[(provider, type_hint, weight)])

    def register_processor(
        self,
        processor: Processor,
        type_hint: Optional[object] = None,
        weight: float = 0,
    ) -> InjectionContext:
        """Register `processor` as a processor of `type_hint`.

        Processors are callbacks that are invoked when an injected function returns
        an instance of `type_hint`.

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
        return self.register(processors=[(processor, type_hint, weight)])

    # ------------------------- registration decorators ---------------------------

    @overload
    def mark_provider(
        self,
        func: ProviderVar,
        *,
        type_hint: Optional[object] = None,
        weight: float = 0,
    ) -> ProviderVar:
        ...

    @overload
    def mark_provider(
        self,
        func: Literal[None] = ...,
        *,
        type_hint: Optional[object] = None,
        weight: float = 0,
    ) -> Callable[[ProviderVar], ProviderVar]:
        ...

    def mark_provider(
        self,
        func: Optional[ProviderVar] = None,
        *,
        type_hint: Optional[object] = None,
        weight: float = 0,
    ) -> Union[Callable[[ProviderVar], ProviderVar], ProviderVar]:
        """Decorate `func` as a provider of its first parameter type.

        Note, If func returns `Optional[Type]`, it will be registered as a provider
        for Type.

        Parameters
        ----------
        func : Optional[Provider]
            A function to decorate. If not provided, a decorator is returned.
        type_hint : Optional[object]
            Optional type or type hint for which to register this provider. If not
            provided, the return annotation of `func` will be used.
        weight : float
            A weight with which to sort this provider. Higher weights are given
            priority, by default 0

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

        def _deco(func: ProviderVar) -> ProviderVar:
            try:
                self.register_provider(func, type_hint=type_hint, weight=weight)
            except ValueError as e:
                warnings.warn(str(e))
            return func

        return _deco(func) if func is not None else _deco

    @overload
    def mark_processor(
        self,
        func: ProcessorVar,
        *,
        type_hint: Optional[object] = None,
        weight: float = 0,
    ) -> ProcessorVar:
        ...

    @overload
    def mark_processor(
        self,
        func: Literal[None] = ...,
        *,
        type_hint: Optional[object] = None,
        weight: float = 0,
    ) -> Callable[[ProcessorVar], ProcessorVar]:
        ...

    def mark_processor(
        self,
        func: Optional[ProcessorVar] = None,
        *,
        type_hint: Optional[object] = None,
        weight: float = 0,
    ) -> Union[Callable[[ProcessorVar], ProcessorVar], ProcessorVar]:
        """Decorate `func` as a processor of its first parameter type.

        Parameters
        ----------
        func : Optional[Processor], optional
            A function to decorate. If not provided, a decorator is returned.
        type_hint : Optional[object]
            Optional type or type hint that this processor can handle. If not
            provided, the type hint of the first parameter of `func` will be used.
        weight : float, optional
            A weight with which to sort this processor. Higher weights are given
            priority, by default 0.  When invoking processors, all processors
            will be invoked in descending weight order, unless `first_processor_only`
            is set to `True`.

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

        def _deco(func: ProcessorVar) -> ProcessorVar:
            try:
                self.register_processor(func, type_hint=type_hint, weight=weight)
            except ValueError as e:
                warnings.warn(str(e))
            return func

        return _deco(func) if func is not None else _deco

    # ------------------------- Callback retrieval ------------------------------

    def iter_providers(
        self, type_hint: Union[object, Type[T]]
    ) -> Iterable[Callable[[], Optional[T]]]:
        """Iterate over all providers of `type_hint`.

        Parameters
        ----------
        type_hint : Union[object, Type[T]]
            A type or type hint for which to return providers.

        Yields
        ------
        Iterable[Callable[[], Optional[T]]]
            Iterable of provider callbacks.
        """
        return self._iter_type_map(type_hint, self._cached_provider_map)

    def iter_processors(
        self, type_hint: Union[object, Type[T]]
    ) -> Iterable[Callable[[T], Any]]:
        """Iterate over all processors of `type_hint`.

        Parameters
        ----------
        type_hint : Union[object, Type[T]]
            A type or type hint for which to return processors.

        Yields
        ------
        Iterable[Callable[[], Optional[T]]]
            Iterable of processor callbacks.
        """
        return self._iter_type_map(type_hint, self._cached_processor_map)

    # ------------------------- Instance retrieval ------------------------------

    def provide(self, type_hint: Union[object, Type[T]]) -> Optional[T]:
        """Provide an instance of `type_hint`.

        This will iterate over all providers of `type_hint` and return the first
        one that returns a non-`None` value.

        Parameters
        ----------
        type_hint : Union[object, Type[T]]
            A type or type hint for which to return a value

        Returns
        -------
        Optional[T]
            The first non-`None` value returned by a provider, or `None` if no
            providers return a value.
        """
        for provider in self.iter_providers(type_hint):
            result = provider()
            if result is not None:
                return result
        return None

    def process(
        self,
        result: Any,
        *,
        type_hint: Union[object, Type[T], None] = None,
        first_processor_only: bool = False,
        raise_exception: bool = False,
    ) -> None:
        """Provide an instance of `type_`.

        This will iterate over all providers of `type_` and invoke the first
        one that accepts `result`, unless `first_processor_only` is set to `False`,
        in which case all processors will be invoked.

        Parameters
        ----------
        result : Any
            The result to process
        type_hint : Union[object, Type[T], None],
            An optional type hint to provide to the processor.  If not provided,
            the type of `result` will be used.
        first_processor_only : bool, optional
            If `True`, only the first processor will be invoked, otherwise all
            processors will be invoked, in descending weight order.
        raise_exception : bool, optional
            If `True`, and a processor raises an exception, it will be raised
            and the remaining processors will not be invoked.
        """
        if type_hint is None:
            type_hint = type(result)
        for processor in self.iter_processors(type_hint):  # type: ignore
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

    # ----------------------Injection decorators ------------------------------------

    @overload
    def inject(
        self,
        func: Callable[P, R],
        *,
        providers: bool = True,
        processors: bool = False,
        localns: Optional[dict] = None,
        on_unresolved_required_args: Optional[RaiseWarnReturnIgnore] = None,
        on_unannotated_required_args: Optional[RaiseWarnReturnIgnore] = None,
    ) -> Callable[P, R]:
        ...

    @overload
    def inject(
        self,
        func: Literal[None] = None,
        *,
        providers: bool = True,
        processors: bool = False,
        localns: Optional[dict] = None,
        on_unresolved_required_args: Optional[RaiseWarnReturnIgnore] = None,
        on_unannotated_required_args: Optional[RaiseWarnReturnIgnore] = None,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        ...

    def inject(
        self,
        func: Optional[Callable[P, R]] = None,
        *,
        providers: bool = True,
        processors: bool = False,
        localns: Optional[dict] = None,
        on_unresolved_required_args: Optional[RaiseWarnReturnIgnore] = None,
        on_unannotated_required_args: Optional[RaiseWarnReturnIgnore] = None,
    ) -> Union[Callable[P, R], Callable[[Callable[P, R]], Callable[P, R]]]:
        """Decorate `func` to inject dependencies at calltime.

        Assuming `providers` is True (the default), this will attempt retrieve
        instances of the types required by `func` and inject them into `func` at
        calltime.  The primary consequence of this is that `func` may be called
        without parameters (assuming the required providers have been registered).
        See usages examples below.

        Note that an injected function may *still* be explicitly invoked with
        parameters.

        See `register` for more information on how to register providers and processors.

        Parameters
        ----------
        func : Callable
            A function to decorate. Type hints are used to determine what to inject.
        providers : bool
            Whether to inject dependency providers. If `True` (default), then when this
            function is called, arguments will be injected into the function call
            according to providers that have been registered in the store.
        processors : bool
            Whether to invoke all processors for this function's return type the when
            this function is called. Important: this causes *side effects*. By default,
            `False`. Output processing can also be enabled (with additionl fine tuning)
            by using the `@store.process_result` decorator.
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

        Examples
        --------
        >>> import in_n_out as ino
        >>> class Thing:
        ...     def __init__(self, name: str):
        ...         self.name = name
        >>> @ino.inject
        ... def func(thing: Thing):
        ...     return thing.name

        >>> # no providers available yet
        >>> func()
        TypeError: ... missing 1 required positional argument: 'thing'

        >>> # register a provider
        >>> ino.register(providers={Thing: Thing('Thing1')})
        >>> print(func())
        'Thing1'

        >>> # can still override with parameters
        >>> func(Thing('OtherThing'))
        'OtherThing'
        """
        on_unres = on_unresolved_required_args or self.on_unresolved_required_args
        on_unann = on_unannotated_required_args or self.on_unannotated_required_args

        # inner decorator, allows for optional decorator arguments
        def _inner(func: Callable[P, R]) -> Callable[P, R]:
            # if the function takes no arguments and has no return annotation
            # there's nothing to be done
            if not providers:
                return self.inject_processors(func) if processors else func

            # bail if there aren't any annotations at all
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

            # get provider functions for each required parameter
            @wraps(func)
            def _exec(*args: P.args, **kwargs: P.kwargs) -> R:
                # we're actually calling the "injected function" now

                _sig = cast("Signature", sig)  # mypy thinks sig is still optional

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

                # call the function with injected values
                try:
                    result = func(**_kwargs)
                except TypeError as e:
                    # likely a required argument is still missing.
                    # show what was injected and raise
                    _argnames = (
                        f"arguments: {', '.join(set(_kwargs))}"
                        if _kwargs
                        else "NO arguments"
                    )
                    raise TypeError(
                        f"After injecting dependencies for {_argnames}, {e}"
                    ) from e

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

            if processors:
                return self.inject_processors(out, type_hint=sig.return_annotation)
            return out

        return _inner(func) if func is not None else _inner

    @overload
    def inject_processors(
        self,
        func: Callable[P, R],
        *,
        type_hint: Union[object, Type[T], None] = None,
        first_processor_only: bool = False,
        raise_exception: bool = False,
    ) -> Callable[P, R]:
        ...

    @overload
    def inject_processors(
        self,
        func: Literal[None] = None,
        *,
        type_hint: Union[object, Type[T], None] = None,
        first_processor_only: bool = False,
        raise_exception: bool = False,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        ...

    def inject_processors(
        self,
        func: Optional[Callable[P, R]] = None,
        *,
        type_hint: Union[object, Type[T], None] = None,
        first_processor_only: bool = False,
        raise_exception: bool = False,
    ) -> Union[Callable[[Callable[P, R]], Callable[P, R]], Callable[P, R]]:
        """Decorate a function to process its output.

        Variant of inject, but only injects processors (for the sake of more explicit
        syntax).

        When the decorated function is called, the return value will be processed
        with `store.process(return_value)` before returning the result.

        Important! This means that calling `func` will likely have *side effects*.

        Parameters
        ----------
        func : Callable
            A function to decorate. Return hints are used to determine what to process.
        type_hint : Union[object, Type[T], None]
            Type hint for the return value.  If not provided, the type will be inferred
            first from the return annotation of the function, and if that is not
            provided, from the `type(return_value)`.
        first_processor_only : bool, optional
            If `True`, only the first processor will be invoked, otherwise all
            processors will be invoked, in descending weight order.
        raise_exception : bool, optional
            If `True`, and a processor raises an exception, it will be raised
            and the remaining processors will not be invoked.

        Returns
        -------
        Callable
            A function that, when called, will have its return value processed by
            `store.process(return_value)`
        """

        def _deco(func: Callable[P, R]) -> Callable[P, R]:
            nonlocal type_hint
            if type_hint is None:
                annotations = getattr(func, "__annotations__", {})
                if "return" in annotations:
                    type_hint = annotations["return"]

            @wraps(func)
            def _exec(*args: P.args, **kwargs: P.kwargs) -> R:
                result = func(*args, **kwargs)
                if result is not None:
                    self.process(
                        result,
                        type_hint=type_hint,
                        first_processor_only=first_processor_only,
                        raise_exception=raise_exception,
                    )
                return result

            return _exec

        return _deco(func) if func is not None else _deco

    # ----------------------  Private methods ----------------------- #

    @cached_property
    def _cached_provider_map(self) -> _CachedMap:
        return self._build_map(self._providers)

    @cached_property
    def _cached_processor_map(self) -> _CachedMap:
        return self._build_map(self._processors)

    def _build_map(self, registry: List[_RegisteredCallback]) -> _CachedMap:
        """Build a map of type hints to callbacks.

        This is the sorted and cached version of the map that will be used to resolve
        a provider or processor.  It returns a tuple of two maps.  The first is a map
        of *all* provider/processor type hints, regardless of whether they can be used
        with `is_subclass`.  The second is a map of only "issubclassable" type hints.
        """
        all_: Dict[object, List[_RegisteredCallback]] = {}
        subclassable: Dict[type, List[_RegisteredCallback]] = {}
        for p in registry:
            if p.origin not in all_:
                all_[p.origin] = []
            all_[p.origin].append(p)
            if p.subclassable:
                if p.origin not in subclassable:
                    subclassable[p.origin] = []
                subclassable[p.origin].append(p)

        all_out = {
            hint: [v.callback for v in sorted(val, key=self._sort_key, reverse=True)]
            for hint, val in all_.items()
        }
        subclassable_out = {
            hint: [v.callback for v in sorted(val, key=self._sort_key, reverse=True)]
            for hint, val in subclassable.items()
        }
        return _CachedMap(all_out, subclassable_out)

    def _iter_type_map(
        self, hint: Union[object, Type[T]], callback_map: _CachedMap
    ) -> Iterable[Callable]:
        _all_types = callback_map.all
        _subclassable_types = callback_map.subclassable

        for origin in _split_union(hint)[0]:
            if origin in _all_types:
                yield from _all_types[origin]
                return

            if isinstance(origin, type):
                # we need origin to be a type to be able to check if it's a
                # subclass of other types
                for _hint, processor in _subclassable_types.items():
                    if issubclass(origin, _hint):
                        yield from processor
                        return

    def _sort_key(self, p: _RegisteredCallback) -> float:
        """How we sort registered callbacks within the same type hint."""
        return p.weight

    def _register_callbacks(
        self,
        callbacks: CallbackIterable,
        providers: bool = True,
    ) -> Disposer:

        if providers:
            reg = self._providers
            cache_map = "_cached_provider_map"
            check_callback: Callable[[Any], Callable] = _validate_provider
            err_msg = (
                "{} has no return type hint (and no hint provided at "
                "registration). Cannot be a provider."
            )

            def _type_from_hints(hints: Dict[str, Any]) -> Any:
                return hints.get("return")

        else:
            reg = self._processors
            cache_map = "_cached_processor_map"
            check_callback = _validate_processor
            err_msg = (
                "{} has no argument type hints (and no hint provided "
                "at registration). Cannot be a processor."
            )

            def _type_from_hints(hints: Dict[str, Any]) -> Any:
                return next((v for k, v in hints.items() if k != "return"), None)

        _callbacks: Iterable[CallbackTuple]
        if isinstance(callbacks, Mapping):
            _callbacks = ((v, k) for k, v in callbacks.items())
        else:
            _callbacks = callbacks

        to_register: List[_RegisteredCallback] = []
        for tup in _callbacks:
            callback, *rest = tup
            type_: Optional[HintArg] = None
            weight: float = 0
            if rest:
                if len(rest) == 1:
                    type_ = rest[0]
                    weight = 0
                elif len(rest) == 2:
                    type_, weight = cast(Tuple[Optional[HintArg], float], rest)
                else:  # pragma: no cover
                    raise ValueError(f"Invalid callback tuple: {tup!r}")

            if type_ is None:
                hints = resolve_type_hints(callback, localns=self.namespace)
                type_ = _type_from_hints(hints)
                if type_ is None:
                    raise ValueError(err_msg.format(callback))

            callback = check_callback(callback)

            if isinstance(callback, types.MethodType):
                # if the callback is a method, we need to wrap it in a weakref
                # to prevent a strong reference to the owner object.
                callback = self._methodwrap(callback, reg, cache_map)

            origins, is_opt = _split_union(type_)
            for origin in origins:
                subclassable: bool = True
                if not issubclassable(origin):
                    subclassable = False
                    try:
                        hash(origin)
                    except TypeError:
                        regname = "provider" if providers else "processor"
                        raise TypeError(
                            f"{origin!r} cannot be used as a {regname} hint, since it "
                            "is not hashable and cannot be passed as the second "
                            "argument to `issubclass`"
                        ) from None

                cb = _RegisteredCallback(origin, callback, is_opt, weight, subclassable)
                to_register.append(cb)

        def _dispose() -> None:
            for p in to_register:
                with contextlib.suppress(ValueError):
                    reg.remove(p)
            # attribute error in case the cache was never built
            with contextlib.suppress(AttributeError):
                delattr(self, cache_map)

        if to_register:
            reg.extend(to_register)
            # attribute error in case the cache was never built
            with contextlib.suppress(AttributeError):
                delattr(self, cache_map)

        return _dispose

    def _methodwrap(
        self, callback: types.MethodType, reg: List[_RegisteredCallback], cache_map: str
    ) -> Callable:
        """Wrap a method in a weakref to prevent a strong reference to the owner."""
        ref = weakref.WeakMethod(callback)

        def _callback(*args: Any, **kwargs: Any) -> Any:
            cb = ref()
            if cb is not None:
                return cb(*args, **kwargs)

            # The callback was garbage collected.  Remove it from the registry.
            for item in reversed(reg):
                if item.callback is _callback:
                    reg.remove(item)

            # attribute error in case the cache was never built
            with contextlib.suppress(AttributeError):
                delattr(self, cache_map)

        return _callback


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


# create the global store
Store._instances[_GLOBAL] = GLOBAL_STORE = Store(_GLOBAL)
