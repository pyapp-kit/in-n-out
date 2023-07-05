from __future__ import annotations

from textwrap import indent
from typing import TYPE_CHECKING, Any, Callable, Iterable, Literal, overload

from ._store import InjectionContext, Store

if TYPE_CHECKING:
    from ._store import (
        P,
        Processor,
        ProcessorIterable,
        ProcessorVar,
        Provider,
        ProviderIterable,
        ProviderVar,
        R,
        T,
    )
    from ._type_resolution import RaiseWarnReturnIgnore

_STORE_PARAM = """
store : Union[Store, str None]
    The store instance or store name to use, if not provided the
    global store is used.
"""
_STORE_PARAM = indent(_STORE_PARAM.strip(), "        ")


def _add_store_to_doc(func: T) -> T:
    new_doc: list[str] = []

    store_doc: str = getattr(Store, func.__name__).__doc__  # type: ignore
    for n, line in enumerate(store_doc.splitlines()):
        if line.lstrip().startswith("Returns"):
            new_doc.insert(n - 1, _STORE_PARAM)

        # TODO: use re.sub instead
        new_doc.append(line.replace(" store.", " ").replace("@store.", "@"))

    func.__doc__ = "\n".join(new_doc)
    return func


def _store_or_global(store: str | Store | None = None) -> Store:
    return store if isinstance(store, Store) else Store.get_store(store)


@_add_store_to_doc
def register(
    *,
    processors: ProcessorIterable | None = None,
    providers: ProviderIterable | None = None,
    store: str | Store | None = None,
) -> InjectionContext:
    return _store_or_global(store).register(providers=providers, processors=processors)


@_add_store_to_doc
def register_provider(
    provider: Provider,
    type_hint: object | None = None,
    weight: float = 0,
    store: str | Store | None = None,
) -> InjectionContext:
    return _store_or_global(store).register_provider(
        provider=provider, type_hint=type_hint, weight=weight
    )


@_add_store_to_doc
def register_processor(
    processor: Processor,
    type_hint: object | None = None,
    weight: float = 0,
    store: str | Store | None = None,
) -> InjectionContext:
    return _store_or_global(store).register_processor(
        processor=processor, type_hint=type_hint, weight=weight
    )


@overload
def mark_provider(
    func: ProviderVar,
    *,
    weight: float = 0,
    type_hint: object | None = None,
    store: str | Store | None = None,
) -> ProviderVar:
    ...


@overload
def mark_provider(
    func: Literal[None] = ...,
    *,
    weight: float = 0,
    type_hint: object | None = None,
    store: str | Store | None = None,
) -> Callable[[ProviderVar], ProviderVar]:
    ...


@_add_store_to_doc
def mark_provider(
    func: ProviderVar | None = None,
    *,
    weight: float = 0,
    type_hint: object | None = None,
    store: str | Store | None = None,
) -> Callable[[ProviderVar], ProviderVar] | ProviderVar:
    return _store_or_global(store).mark_provider(
        func, weight=weight, type_hint=type_hint
    )


@overload
def mark_processor(
    func: ProcessorVar,
    *,
    weight: float = 0,
    type_hint: object | None = None,
    store: str | Store | None = None,
) -> ProcessorVar:
    ...


@overload
def mark_processor(
    func: Literal[None] = ...,
    *,
    weight: float = 0,
    type_hint: object | None = None,
    store: str | Store | None = None,
) -> Callable[[ProcessorVar], ProcessorVar]:
    ...


@_add_store_to_doc
def mark_processor(
    func: ProcessorVar | None = None,
    *,
    weight: float = 0,
    type_hint: object | None = None,
    store: str | Store | None = None,
) -> Callable[[ProcessorVar], ProcessorVar] | ProcessorVar:
    return _store_or_global(store).mark_processor(
        func, weight=weight, type_hint=type_hint
    )


@_add_store_to_doc
def iter_providers(
    type_hint: object | type[T], store: str | Store | None = None
) -> Iterable[Callable[[], T | None]]:
    return _store_or_global(store).iter_providers(type_hint)


@_add_store_to_doc
def iter_processors(
    type_hint: object | type[T], store: str | Store | None = None
) -> Iterable[Callable[[T], Any]]:
    return _store_or_global(store).iter_processors(type_hint)


@_add_store_to_doc
def provide(
    type_hint: object | type[T],
    store: str | Store | None = None,
) -> T | None:
    return _store_or_global(store).provide(type_hint=type_hint)


@_add_store_to_doc
def process(
    result: Any,
    *,
    type_hint: object | type[T] | None = None,
    first_processor_only: bool = False,
    raise_exception: bool = False,
    store: str | Store | None = None,
) -> None:
    return _store_or_global(store).process(
        result=result,
        type_hint=type_hint,
        first_processor_only=first_processor_only,
        raise_exception=raise_exception,
    )


@overload
def inject(
    func: Callable[P, R],
    *,
    providers: bool = True,
    processors: bool = False,
    localns: dict | None = None,
    on_unresolved_required_args: RaiseWarnReturnIgnore | None = None,
    on_unannotated_required_args: RaiseWarnReturnIgnore | None = None,
    guess_self: bool | None = None,
    store: str | Store | None = None,
) -> Callable[..., R]:
    ...
    # unfortunately, the best we can do is convert the signature to Callabe[..., R]
    # so we lose the parameter information.  but it seems better than having
    # "missing positional args" errors everywhere on injected functions.


@overload
def inject(
    func: Literal[None] | None = None,
    *,
    providers: bool = True,
    processors: bool = False,
    localns: dict | None = None,
    on_unresolved_required_args: RaiseWarnReturnIgnore | None = None,
    on_unannotated_required_args: RaiseWarnReturnIgnore | None = None,
    guess_self: bool | None = None,
    store: str | Store | None = None,
) -> Callable[[Callable[P, R]], Callable[..., R]]:
    ...


@_add_store_to_doc
def inject(
    func: Callable[P, R] | None = None,
    *,
    providers: bool = True,
    processors: bool = False,
    localns: dict | None = None,
    on_unresolved_required_args: RaiseWarnReturnIgnore | None = None,
    on_unannotated_required_args: RaiseWarnReturnIgnore | None = None,
    guess_self: bool | None = None,
    store: str | Store | None = None,
) -> Callable[..., R] | Callable[[Callable[P, R]], Callable[..., R]]:
    return _store_or_global(store).inject(
        func=func,
        providers=providers,
        processors=processors,
        localns=localns,
        on_unresolved_required_args=on_unresolved_required_args,
        on_unannotated_required_args=on_unannotated_required_args,
        guess_self=guess_self,
    )


@overload
def inject_processors(
    func: Callable[P, R],
    *,
    hint: object | type[T] | None = None,
    first_processor_only: bool = False,
    raise_exception: bool = False,
    store: str | Store | None = None,
) -> Callable[P, R]:
    ...


@overload
def inject_processors(
    func: Literal[None] | None = None,
    *,
    hint: object | type[T] | None = None,
    first_processor_only: bool = False,
    raise_exception: bool = False,
    store: str | Store | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    ...


@_add_store_to_doc
def inject_processors(
    func: Callable[P, R] | None = None,
    *,
    hint: object | type[T] | None = None,
    first_processor_only: bool = False,
    raise_exception: bool = False,
    store: str | Store | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]] | Callable[P, R]:
    return _store_or_global(store).inject_processors(
        func=func,
        type_hint=hint,
        first_processor_only=first_processor_only,
        raise_exception=raise_exception,
    )
