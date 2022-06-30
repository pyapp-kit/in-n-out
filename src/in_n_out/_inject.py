from __future__ import annotations

import warnings
from functools import wraps
from inspect import isgeneratorfunction
from typing import TYPE_CHECKING, Any, Dict, List, Union, overload

from ._store import Store
from ._type_resolution import type_resolved_signature

if TYPE_CHECKING:
    from inspect import Signature
    from typing import Callable, Literal, Optional, TypeVar

    from typing_extensions import ParamSpec

    P = ParamSpec("P")
    R = TypeVar("R")
    RaiseWarnReturnIgnore = Literal["raise", "warn", "return", "ignore"]


@overload
def inject_dependencies(
    func: Callable[P, R],
    *,
    localns: Optional[dict] = None,
    store: Union[str, Store, None] = None,
    on_unresolved_required_args: RaiseWarnReturnIgnore = "raise",
    on_unannotated_required_args: RaiseWarnReturnIgnore = "warn",
) -> Callable[P, R]:
    ...


@overload
def inject_dependencies(
    func: Literal[None] = None,
    *,
    localns: Optional[dict] = None,
    store: Union[str, Store, None] = None,
    on_unresolved_required_args: RaiseWarnReturnIgnore = "raise",
    on_unannotated_required_args: RaiseWarnReturnIgnore = "warn",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    ...


def inject_dependencies(
    func: Optional[Callable[P, R]] = None,
    *,
    localns: Optional[dict] = None,
    store: Union[str, Store, None] = None,
    on_unresolved_required_args: RaiseWarnReturnIgnore = "raise",
    on_unannotated_required_args: RaiseWarnReturnIgnore = "warn",
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

    # inner decorator, allows for optional decorator arguments
    def _inner(func: Callable[P, R]) -> Callable[P, R]:
        # if the function takes no arguments and has no return annotation
        # there's nothing to be done
        if not func.__code__.co_argcount and "return" not in getattr(
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
            localns={**_store.namespace, **(localns or {})},
            on_unresolved_required_args=on_unresolved_required_args,
            on_unannotated_required_args=on_unannotated_required_args,
        )
        if sig is None:  # something went wrong, and the user was notified.
            return func
        process_result = sig.return_annotation is not sig.empty
        return_anno = sig.return_annotation

        names: List[str] = list(sig.parameters)
        hints = [p.annotation for p in sig.parameters.values()]

        # get provider functions for each required parameter
        @wraps(func)
        def _exec(*args: P.args, **kwargs: P.kwargs) -> R:
            # sourcery skip: use-named-expression
            # we're actually calling the "injected function" now

            # first, get and call the provider functions for each parameter type:
            _kwargs = {}
            for n, name in enumerate(names):
                provider: Optional[Callable] = _store._get_provider(hints[n])
                if provider:
                    _kwargs[name] = provider()

            # this would be a safer way to merge arguments, but it's much slower
            # bound = sig.bind_partial(*args, **kwargs)  # type: ignore
            # bound.apply_defaults()
            # _kwargs.update(**bound.arguments)

            # significantly faster
            _argdict: Dict[str, Any] = dict(zip(names, args))  # type: ignore
            assert all(i not in _argdict for i in kwargs)
            _kwargs.update(_argdict)
            _kwargs.update(kwargs)

            try:  # call the function with injected values
                result = func(**_kwargs)
            except TypeError as e:
                # likely a required argument is still missing.
                raise TypeError(
                    f"After injecting dependencies for arguments {set(_kwargs)}, {e}"
                ) from e

            if result is not None and process_result:
                processor = _store._get_processor(return_anno)
                if processor:
                    processor(result)

            return result

        out = _exec

        # if it came in as a generatorfunction, it needs to go out as one.
        if isgeneratorfunction(func):

            @wraps(func)
            def _gexec(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore [misc]
                yield from _exec(*args, **kwargs)  # type: ignore [misc]

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
        out._dependencies_injected = True  # type: ignore [attr-defined]
        return out

    return _inner(func) if func is not None else _inner


def _resolve_sig_or_inform(
    func: Callable,
    localns: Optional[dict],
    on_unresolved_required_args: RaiseWarnReturnIgnore,
    on_unannotated_required_args: RaiseWarnReturnIgnore,
) -> Optional[Signature]:
    """Helper function for user warnings/errors during inject_dependencies.

    all parameters are described above in inject_dependencies
    """
    try:
        sig = type_resolved_signature(
            func, localns=localns, raise_unresolved_optional_args=False
        )
    except NameError as e:
        errmsg = str(e)
        if on_unresolved_required_args == "raise":
            msg = (
                f"{errmsg}. To simply return the original function, pass `on_un"
                'resolved_required_args="return"`. To emit a warning, pass "warn".'
            )
            raise NameError(msg) from e
        if on_unresolved_required_args == "warn":
            msg = (
                f"{errmsg}. To suppress this warning and simply return the original "
                'function, pass `on_unresolved_required_args="return"`.'
            )

            warnings.warn(msg, UserWarning, stacklevel=2)
        return None

    for param in sig.parameters.values():
        if param.default is param.empty and param.annotation is param.empty:
            fname = (getattr(func, "__name__", ""),)
            name = param.name
            base = (
                f"Injecting dependencies on function {fname!r} with a required, "
                f"unannotated parameter {name!r}. This will fail later unless that "
                "parameter is provided at call-time.",
            )
            if on_unannotated_required_args == "raise":
                msg = (
                    f'{base} To allow this, pass `on_unannotated_required_args="ignore"'
                    '`. To emit a warning, pass "warn".'
                )
                raise TypeError(msg)
            elif on_unannotated_required_args == "warn":
                msg = (
                    f'{base} To allow this, pass `on_unannotated_required_args="ignore"'
                    '`. To raise an exception, pass "raise".'
                )
                warnings.warn(msg, UserWarning, stacklevel=2)
            elif on_unannotated_required_args == "return":
                return None

    return sig
