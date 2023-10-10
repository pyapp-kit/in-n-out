from __future__ import annotations

import sys
import types
import typing
import warnings
from functools import lru_cache, partial
from inspect import Signature
from typing import TYPE_CHECKING, Any, Callable, ForwardRef

try:
    from toolz import curry

    PARTIAL_TYPES: tuple[type, ...] = (partial, curry)
except ImportError:  # pragma: no cover
    PARTIAL_TYPES = (partial,)

if TYPE_CHECKING:
    from typing import Literal, _get_type_hints_obj_allowed_types

    RaiseWarnReturnIgnore = Literal["raise", "warn", "return", "ignore"]

PY39_OR_GREATER = sys.version_info >= (3, 9)


@lru_cache(maxsize=1)
def _typing_names() -> dict[str, Any]:
    return {**typing.__dict__, **types.__dict__}


def _unwrap_partial(func: Any) -> Any:
    while isinstance(func, PARTIAL_TYPES):
        func = func.func
    return func


def resolve_type_hints(
    obj: _get_type_hints_obj_allowed_types,
    globalns: dict | None = None,
    localns: dict | None = None,
    include_extras: bool = False,
) -> dict[str, Any]:
    """Return type hints for an object.

    This is a small wrapper around `typing.get_type_hints()` that adds
    namespaces to the global and local namespaces.

    see docstring for :func:`typing.get_type_hints`.

    Parameters
    ----------
    obj : module, class, method, or function
        must be a module, class, method, or function.
    globalns : Optional[dict]
        optional global namespace, by default None.
    localns : Optional[dict]
        optional local namespace, by default None.
    include_extras : bool
        If `False` (the default), recursively replaces all 'Annotated[T, ...]'
        with 'T'.

    Returns
    -------
    Dict[str, Any]
        mapping of object name to type hint for all annotated attributes of `obj`.
    """
    _localns = dict(_typing_names())
    if localns:
        _localns.update(localns)  # explicitly provided locals take precedence
    kwargs: dict[str, Any] = {"globalns": globalns, "localns": _localns}
    if PY39_OR_GREATER:
        kwargs["include_extras"] = include_extras
    return typing.get_type_hints(_unwrap_partial(obj), **kwargs)


def resolve_single_type_hints(
    *objs: Any,
    globalns: dict | None = None,
    localns: dict | None = None,
    include_extras: bool = False,
) -> tuple[Any, ...]:
    """Get type hints for one or more isolated type annotations.

    Wrapper around :func:`resolve_type_hints` (see docstring for that function for
    parameter docs).

    `typing.get_type_hints()` only works for modules, classes, methods, or functions,
    but the typing module doesn't make the underlying type evaluation logic publicly
    available. This function creates a small mock object with an `__annotations__`
    dict that will work as an argument to `typing.get_type_hints()`.  It then extracts
    the resolved hints back into a tuple of hints corresponding to the input objects.

    Returns
    -------
    Tuple[Any, ...]
        Tuple

    >>> resolve_single_type_hints('hi', localns={'hi': typing.Any})
    (typing.Any,)
    """
    annotations = {str(n): v for n, v in enumerate(objs)}
    mock_obj = type("_T", (), {"__annotations__": annotations})()
    hints = resolve_type_hints(
        mock_obj, globalns=globalns, localns=localns, include_extras=include_extras
    )
    return tuple(hints[k] for k in annotations)


def type_resolved_signature(
    func: Callable,
    *,
    localns: dict | None = None,
    raise_unresolved_optional_args: bool = True,
    raise_unresolved_required_args: bool = True,
    guess_self: bool = True,
) -> Signature:
    """Return a Signature object for a function with resolved type annotations.

    Parameters
    ----------
    func : Callable
        A callable object.
    localns : Optional[dict]
        Optional local namespace for name resolution, by default None
    raise_unresolved_optional_args : bool
        Whether to raise an exception when an optional parameter (one with a default
        value) has an unresolvable type annotation, by default True
    raise_unresolved_required_args : bool
        Whether to raise an exception when a required parameter has an unresolvable
        type annotation, by default True
    guess_self : bool
        Whether to infer the type of the first argument if the function is an unbound
        class method. This is done as follows:
            - if '.' (but not '<locals>') is in the function's __qualname__
            - and if the first parameter is named 'self' or starts with "_"
            - and if the first parameter annotation is `inspect.empty`
            - then the name preceding `func.__name__` in the function's __qualname__
              (which is usually the class name), is looked up in the function's
              `__globals__` namespace. If found, it is used as the first parameter's
              type annotation.
        This allows class methods to be injected with instances of the class.

    Returns
    -------
    Signature
        :class:`inspect.Signature` object with fully resolved type annotations,
        (or at least partially resolved type annotations if
        `raise_unresolved_optional_args` is `False`).

    Raises
    ------
    NameError
        If a required argument has an unresolvable type annotation, or if
        `raise_unresolved_optional_args` is `True` and an optional argument has
        an unresolvable type annotation.
    """
    sig = Signature.from_callable(func)
    hints = {}
    if guess_self and sig.parameters:
        p0 = next(iter(sig.parameters.values()))
        # The best identifier i can figure for a class method is that:
        # 1. its qualname contains a period (e.g. "MyClass.my_method"),
        # 2. the first parameter tends to be named "self", or some private variable
        # 3. the first parameter tends to be unannotated
        qualname = getattr(func, "__qualname__", "")
        if (
            "." in qualname
            and "<locals>" not in qualname  # don't support locally defd types
            and (p0.name == "self" or p0.name.startswith("_"))
            and p0.annotation is p0.empty
        ):
            # look up the class name in the function's globals
            cls_name = qualname.replace(func.__name__, "").rstrip(".")
            func_globals = getattr(func, "__globals__", {})
            if cls_name in func_globals:
                # add it to the type hints
                hints = {p0.name: func_globals[cls_name]}

    try:
        hints.update(resolve_type_hints(func, localns=localns))
    except (NameError, TypeError) as err:
        if raise_unresolved_optional_args:
            raise NameError(
                f"Could not resolve all annotations in signature {sig} ({err}). "
                "To allow optional parameters and return types to remain unresolved, "
                "use `raise_unresolved_optional_args=False`"
            ) from err
        hints = _resolve_params_one_by_one(
            sig,
            globalns=getattr(func, "__globals__", None),
            localns=localns,
            exclude_unresolved_mandatory=not raise_unresolved_required_args,
        )

    resolved_parameters = [
        param.replace(annotation=hints.get(param.name, param.empty))
        for param in sig.parameters.values()
    ]
    return sig.replace(
        parameters=resolved_parameters,
        return_annotation=hints.get("return", sig.empty),
    )


def _resolve_params_one_by_one(
    sig: Signature,
    globalns: dict | None = None,
    localns: dict | None = None,
    exclude_unresolved_optionals: bool = False,
    exclude_unresolved_mandatory: bool = False,
) -> dict[str, Any]:
    """Resolve all required param annotations in `sig`, but allow optional ones to fail.

    Helper function for :func:`type_resolved_signature`.  This fallback function is
    used if at least one parameter in `sig` has an unresolvable type annotation.
    It resolves each parameter's type annotation independently, and only raises an
    error if a parameter without a default value has an unresolvable type annotation.

    Parameters
    ----------
    sig : Signature
        :class:`inspect.Signature` object with unresolved type annotations.
    globalns : Optional[dict]
        Optional global namespace for name resolution, by default None
    localns : Optional[dict]
        Optional local namespace for name resolution, by default None
    exclude_unresolved_optionals : bool
        Whether to exclude parameters with unresolved type annotations that have a
        default value, by default False
    exclude_unresolved_mandatory : bool
        Whether to exclude parameters with unresolved type annotations that do not
        have a default value, by default False

    Returns
    -------
    Dict[str, Any]
        mapping of parameter name to type hint.

    Raises
    ------
    NameError
        If a required argument has an unresolvable type annotation.
    """
    hints = {}
    for name, param in sig.parameters.items():
        if param.annotation is sig.empty:
            continue  # pragma: no cover
        try:
            hints[name] = resolve_single_type_hints(
                param.annotation, globalns=globalns, localns=localns
            )[0]
        except NameError as e:
            if (
                param.default is param.empty
                and exclude_unresolved_mandatory
                or param.default is not param.empty
                and not exclude_unresolved_optionals
            ):
                hints[name] = param.annotation
            elif param.default is param.empty:
                raise NameError(
                    f"Could not resolve type hint for required parameter {name!r}: {e}"
                ) from e
    if sig.return_annotation is not sig.empty:
        try:
            hints["return"] = resolve_single_type_hints(
                sig.return_annotation, globalns=globalns, localns=localns
            )[0]
        except NameError:
            if not exclude_unresolved_optionals:
                hints["return"] = sig.return_annotation
    return hints


def _resolve_sig_or_inform(
    func: Callable,
    localns: dict | None,
    on_unresolved_required_args: RaiseWarnReturnIgnore,
    on_unannotated_required_args: RaiseWarnReturnIgnore,
    guess_self: bool = True,
) -> Signature | None:
    """Return a resolved signature, or None if the function should be returned as-is.

    Helper function for user warnings/errors during inject_dependencies.

    all parameters are described above in inject_dependencies
    """
    sig = type_resolved_signature(
        func,
        localns=localns,
        raise_unresolved_optional_args=False,
        raise_unresolved_required_args=False,
        guess_self=guess_self,
    )

    for param in sig.parameters.values():
        if param.default is not param.empty:
            continue  # pragma: no cover
        if isinstance(param.annotation, (str, ForwardRef)):
            errmsg = (
                f"Could not resolve type hint for required parameter {param.name!r}"
            )
            if on_unresolved_required_args == "raise":
                msg = (
                    f"{errmsg}. To simply return the original function, pass `on_un"
                    'annotated_required_args="return"`. To emit a warning, pass "warn".'
                )
                raise NameError(msg)
            elif on_unresolved_required_args == "warn":
                msg = (
                    f"{errmsg}. To suppress this warning and simply return the original"
                    ' function, pass `on_unannotated_required_args="return"`.'
                )
                warnings.warn(msg, UserWarning, stacklevel=2)
            elif on_unresolved_required_args == "return":
                return None

        elif param.annotation is param.empty:
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
