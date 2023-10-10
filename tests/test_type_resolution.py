import types
from typing import Any, Callable, Optional

import pytest

from in_n_out import (
    resolve_single_type_hints,
    resolve_type_hints,
    type_resolved_signature,
)
from in_n_out._type_resolution import _resolve_sig_or_inform


def basic_sig(a: "int", b: "str", c: "Optional[float]" = None) -> int:
    ...


def requires_unknown(param: "Unknown", x) -> "Unknown":  # type: ignore # noqa
    ...


def optional_unknown(param: "Unknown" = 1) -> "Unknown":  # type: ignore # noqa
    ...


def test_resolve_type_hints():
    with pytest.raises(NameError):
        resolve_type_hints(requires_unknown)

    hints = resolve_type_hints(basic_sig)
    assert hints["c"] == Optional[float]

    hints = resolve_type_hints(requires_unknown, localns={"Unknown": int})
    assert hints["param"] == int


def test_resolve_single_type_hints():
    hints = resolve_single_type_hints(
        int,
        "Optional[int]",
        "FunctionType",
        "Callable[..., Any]",
    )

    assert hints == (
        int,
        Optional[int],
        types.FunctionType,
        Callable[..., Any],
    )


def test_type_resolved_signature():
    sig = type_resolved_signature(basic_sig)
    assert sig.parameters["c"].annotation == Optional[float]

    with pytest.raises(NameError, match="use `raise_unresolved_optional_args=False`"):
        type_resolved_signature(optional_unknown)

    sig = type_resolved_signature(
        optional_unknown, raise_unresolved_optional_args=False
    )
    assert sig.parameters["param"].annotation == "Unknown"

    with pytest.raises(NameError, match="Could not resolve all annotations"):
        type_resolved_signature(requires_unknown)

    with pytest.raises(
        NameError,
        match="Could not resolve type hint for required parameter 'param'",
    ):
        type_resolved_signature(requires_unknown, raise_unresolved_optional_args=False)

    sig = type_resolved_signature(requires_unknown, localns={"Unknown": int})
    assert sig.parameters["param"].annotation == int


def test_partial_resolution() -> None:
    from functools import partial

    def func(x: int, y: str, z: list):
        ...

    pf = partial(func, 1)
    ppf = partial(pf, z=["hi"])

    assert resolve_type_hints(ppf) == {"x": int, "y": str, "z": list}


def test_curry_resolution() -> None:
    toolz = pytest.importorskip("toolz")

    @toolz.curry
    def func2(x: int, y: str, z: list):
        ...

    pf = func2(x=1)
    ppf = pf(z=["hi"])

    assert resolve_type_hints(ppf) == {"x": int, "y": str, "z": list}


def test_wrapped_resolution() -> None:
    from functools import wraps

    def func(x: int, y: str, z: list):
        ...

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    @wraps(wrapper)
    def wrapper2(*args, **kwargs):
        return wrapper(*args, **kwargs)

    assert resolve_type_hints(wrapper2) == {"x": int, "y": str, "z": list}


def test_resolve_sig_or_inform():
    """Make sure we can partially resolve annotations."""

    class Foo:
        ...

    def func(foo: "Foo", bar: "Bar"):  # noqa
        return foo, bar

    sig = _resolve_sig_or_inform(
        func,
        localns={"Foo": Foo},
        on_unresolved_required_args="ignore",
        on_unannotated_required_args="ignore",
    )

    assert sig.parameters["foo"].annotation == Foo
    assert sig.parameters["bar"].annotation == "Bar"

    # other way around
    def func2(bar: "Bar", foo: "Foo"):  # noqa
        return foo, bar

    sig2 = _resolve_sig_or_inform(
        func2,
        localns={"Foo": Foo},
        on_unresolved_required_args="ignore",
        on_unannotated_required_args="ignore",
    )

    assert sig2.parameters["foo"].annotation == Foo
    assert sig2.parameters["bar"].annotation == "Bar"


GlobalThing = int


def test_type_resolved_signature_mixed_global() -> None:
    """Test that we can resolve a mix of global annotations and missing forward refs."""

    def myfun(a: "unknown", b: "GlobalThing"):  # type: ignore  # noqa
        pass

    _a = type_resolved_signature(
        myfun,
        raise_unresolved_optional_args=False,
        raise_unresolved_required_args=False,
    )
    assert _a.parameters["a"].annotation == "unknown"
    assert _a.parameters["b"].annotation == int
