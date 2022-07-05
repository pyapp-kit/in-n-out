from __future__ import annotations

from typing import TYPE_CHECKING, Union, overload

from ._store import Store

if TYPE_CHECKING:
    from typing import Callable, Literal, Optional, TypeVar

    from typing_extensions import ParamSpec

    from ._type_resolution import RaiseWarnReturnIgnore

    P = ParamSpec("P")
    R = TypeVar("R")
    OptRaiseWarnReturnIgnore = Optional[RaiseWarnReturnIgnore]


@overload
def inject_dependencies(
    func: Callable[P, R],
    *,
    localns: Optional[dict] = None,
    store: Union[str, Store, None] = None,
    on_unresolved_required_args: OptRaiseWarnReturnIgnore = None,
    on_unannotated_required_args: OptRaiseWarnReturnIgnore = None,
) -> Callable[P, R]:
    ...


@overload
def inject_dependencies(
    func: Literal[None] = None,
    *,
    localns: Optional[dict] = None,
    store: Union[str, Store, None] = None,
    on_unresolved_required_args: OptRaiseWarnReturnIgnore = None,
    on_unannotated_required_args: OptRaiseWarnReturnIgnore = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    ...


def inject_dependencies(
    func: Optional[Callable[P, R]] = None,
    *,
    localns: Optional[dict] = None,
    store: Union[str, Store, None] = None,
    on_unresolved_required_args: OptRaiseWarnReturnIgnore = None,
    on_unannotated_required_args: OptRaiseWarnReturnIgnore = None,
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
    store : Union[str, Store, None]
        Optional store to use when retrieving providers and processors,
        by default the global store will be used.
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
            - 'return': stop decorating, return the original function without warning
            - 'ignore': continue decorating without warning.

    Returns
    -------
    Callable
        A function with dependencies injected
    """
    _store = store if isinstance(store, Store) else Store.get_store(store)
    return _store.inject_dependencies(
        func=func,
        localns=localns,
        on_unresolved_required_args=on_unresolved_required_args,
        on_unannotated_required_args=on_unannotated_required_args,
    )
