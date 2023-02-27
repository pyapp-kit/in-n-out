import sys
from typing import TYPE_CHECKING

import pytest

import in_n_out as ino

if TYPE_CHECKING:
    from pytest import LogCaptureFixture


@pytest.mark.skipif(sys.version_info < (3, 9), reason="output differs on 3.8")
def test_logging(caplog: "LogCaptureFixture") -> None:
    caplog.set_level("DEBUG")

    VAL = "hi"

    def p1() -> str:
        return VAL

    def proc(x: str) -> None:
        ...

    ctx_a = ino.register(providers=[(p1, str)])
    assert caplog.records[0].message.startswith(
        "Registering provider of <class 'str'>: <function test_logging.<locals>.p1"
    )

    ctx_b = ino.register(processors=[(proc, str)])
    assert caplog.records[1].message.startswith(
        "Registering processor of <class 'str'>: <function test_logging.<locals>.proc"
    )

    @ino.inject(processors=True)
    def f(x: str) -> str:
        return x

    f()
    assert [r.message[:50] for r in caplog.records[2:-1]] == [
        "Executing @injected test_logging.<locals>.f(x: str",
        "Rebuilding provider map cache",
        f"  injecting x: <class 'str'> = '{VAL}'",
        f"  Calling test_logging.<locals>.f with {{'x': '{VAL}'}}",
        "Rebuilding processor map cache",
        f"Invoking processors on result '{VAL}' from function '",
    ]
    assert caplog.records[-1].message.startswith(
        "  P: <function test_logging.<locals>.proc at 0"
    )

    ctx_a.cleanup()
    assert caplog.records[-1].message.startswith(
        "Unregistering provider of <class 'str'>: <function test_logging.<locals>.p1"
    )

    ctx_b.cleanup()
    assert caplog.records[-1].message.startswith(
        "Unregistering processor of <class 'str'>: <function test_logging.<locals>.proc"
    )
