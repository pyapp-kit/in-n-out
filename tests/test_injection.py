from contextlib import nullcontext
from typing import ContextManager, Optional
from unittest.mock import Mock

import pytest

from in_n_out import Store, inject, inject_processors, register


def test_injection():
    @inject
    def f(i: int, s: str):
        return (i, s)

    with register(providers={int: lambda: 1, str: lambda: "hi"}):
        assert f() == (1, "hi")


@pytest.mark.parametrize("order", ["together", "inject_first", "inject_last"])
def test_inject_deps_and_providers(order):
    mock = Mock()
    mock2 = Mock()

    def f(i: int) -> str:
        mock(i)
        return str(i)

    if order == "together":
        f = inject(f, providers=True, processors=True)
    elif order == "inject_first":
        f = inject_processors(inject(f))
    elif order == "inject_last":
        f = inject(inject_processors(f))

    with register(providers={int: lambda: 1}, processors={str: mock2}):
        assert f() == "1"
        mock.assert_called_once_with(1)
        mock2.assert_called_once_with("1")


def test_inject_only_providers():
    mock = Mock()

    def f(i: int) -> str:
        mock(i)
        return str(i)

    f2 = inject(f, providers=False, processors=False)
    assert f2 is f

    f3 = inject(f, providers=False, processors=True)
    assert f3 is not f2

    with register(processors={str: mock}):
        assert f(1) == "1"
        mock.assert_called_once_with(1)


def test_injection_missing():
    @inject
    def f(x: int):
        return x

    with pytest.raises(TypeError) as e:
        f()
    assert "missing 1 required positional argument" in str(e.value)
    assert f(4) == 4
    with register(providers={int: lambda: 1}):
        assert f() == 1


def test_set_processor():
    @inject_processors
    def f2(x: int) -> int:
        return x

    # calling mock inside process_int to preserve the __code__ object
    # on the processor function
    mock = Mock()

    def process_int(x: int) -> None:
        mock(x)

    with register(processors={int: process_int}):
        assert f2(3) == 3

    mock.assert_called_once_with(3)


def test_injection_with_generator():
    @inject
    def f(x: int):
        yield x

    # setting the accessor to our local viewer
    with register(providers={int: lambda: 1}):
        assert tuple(f()) == (1,)


def test_injection_without_args():
    """it just returns the same function"""

    def f():
        ...

    assert inject(f) is f


modes = ["raise", "warn", "return", "ignore"]


def unknown(v: "Unknown") -> int:  # type: ignore  # noqa
    ...


def unannotated(x) -> int:  # type: ignore  # noqa
    ...


def unknown_and_unannotated(v: "Unknown", x) -> int:  # type: ignore  # noqa
    ...


@pytest.mark.parametrize("on_unresolved", modes)
@pytest.mark.parametrize("on_unannotated", modes)
@pytest.mark.parametrize("in_func", [unknown, unannotated, unknown_and_unannotated])
def test_injection_errors(in_func, on_unresolved, on_unannotated):

    ctx: ContextManager = nullcontext()
    expect_same_func_back = False

    if "unknown" in in_func.__name__:  # required params with unknown annotations
        if on_unresolved == "raise":
            ctx = pytest.raises(
                NameError,
                match="Could not resolve type hint for required parameter",
            )
        else:
            expect_same_func_back = True
            if on_unresolved == "warn":
                ctx = pytest.warns(
                    UserWarning,
                    match="Could not resolve type hint for required parameter",
                )

    elif "unannotated" in in_func.__name__:  # required params without annotations
        if on_unannotated == "raise":
            ctx = pytest.raises(
                TypeError,
                match="Injecting dependencies .* with a required, unannotated param",
            )
        elif on_unannotated == "warn":
            ctx = pytest.warns(
                UserWarning,
                match="Injecting dependencies .* with a required, unannotated param",
            )
        elif on_unannotated == "return":
            expect_same_func_back = True

    with ctx:
        out_func = inject(
            in_func,
            on_unannotated_required_args=on_unannotated,
            on_unresolved_required_args=on_unresolved,
        )

        if expect_same_func_back:
            assert out_func is in_func
        else:
            assert out_func is not in_func


def test_processors_not_passed_none(test_store: Store):
    @test_store.inject_processors
    def f(x: int) -> Optional[int]:
        return x if x > 5 else None

    mock = Mock()

    # regardless of whether a process accepts "Optional" or not,
    # we won't call it unless the value is not None
    # i.e. this could also be `(x: Optional[int])` and it would only be called with int
    def process_int(x: int) -> None:
        mock(x)

    with test_store.register(processors={int: process_int}):
        assert f(3) is None
        mock.assert_not_called()
        assert f(10) == 10
        mock.assert_called_once_with(10)


def test_optional_provider_with_required_arg(test_store: Store):
    mock = Mock()

    @inject(store=test_store)
    def f(x: int):
        mock(x)

    with test_store.register(providers={Optional[int]: lambda: None}):
        with pytest.raises(TypeError, match="missing 1 required positional argument"):
            f()
        mock.assert_not_called()

    with test_store.register(providers={Optional[int]: lambda: 2}):
        f()
        mock.assert_called_once_with(2)
