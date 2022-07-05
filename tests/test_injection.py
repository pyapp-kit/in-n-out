from contextlib import nullcontext
from typing import ContextManager, Optional
from unittest.mock import Mock

import pytest

from in_n_out import inject_dependencies, set_processors, set_providers


def test_injection():
    @inject_dependencies
    def f(i: int, s: str):
        return (i, s)

    with set_providers({int: lambda: 1, str: lambda: "hi"}):
        assert f() == (1, "hi")


def test_injection_missing():
    @inject_dependencies
    def f(x: int):
        return x

    with pytest.raises(TypeError) as e:
        f()
    assert "missing 1 required positional argument" in str(e.value)
    assert f(4) == 4
    with set_providers({int: lambda: 1}):
        assert f() == 1


def test_set_processor():
    @inject_dependencies
    def f2(x: int) -> int:
        return x

    # calling mock inside process_int to preserve the __code__ object
    # on the processor function
    mock = Mock()

    def process_int(x: int) -> None:
        print("HI")
        mock(x)

    with set_processors({int: process_int}):
        assert f2(3) == 3

    mock.assert_called_once_with(3)


def test_injection_with_generator():
    @inject_dependencies
    def f(x: int):
        yield x

    # setting the accessor to our local viewer
    with set_providers({int: lambda: 1}):
        assert tuple(f()) == (1,)


def test_injection_without_args():
    """it just returns the same function"""

    def f():
        ...

    assert inject_dependencies(f) is f


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
        out_func = inject_dependencies(
            in_func,
            on_unannotated_required_args=on_unannotated,
            on_unresolved_required_args=on_unresolved,
        )

        if expect_same_func_back:
            assert out_func is in_func
        else:
            assert out_func is not in_func


def test_processors_not_passed_none():
    @inject_dependencies
    def f(x: int) -> Optional[int]:
        return x if x > 5 else None

    mock = Mock()

    # regardless of whether a process accepts "Optional" or not,
    # we won't call it unless the value is not None
    # i.e. this could also be `(x: Optional[int])` and it would only be called with int
    def process_int(x: int) -> None:
        mock(x)

    with set_processors({int: process_int}):
        assert f(3) is None
        mock.assert_not_called()
        assert f(10) == 10
        mock.assert_called_once_with(10)


def test_optional_provider_with_required_arg(test_store):
    mock = Mock()

    @inject_dependencies(store=test_store)
    def f(x: int):
        mock(x)

    with set_providers({Optional[int]: lambda: None}, store=test_store):
        with pytest.raises(TypeError, match="missing 1 required positional argument"):
            f()
        mock.assert_not_called()

    with set_providers({Optional[int]: lambda: 2}, store=test_store):
        f()
        mock.assert_called_once_with(2)
