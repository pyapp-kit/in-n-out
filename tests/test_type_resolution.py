import types
from typing import Any, Callable, Optional

import pytest

from in_n_out import (
    resolve_single_type_hints,
    resolve_type_hints,
    type_resolved_signature,
)


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
