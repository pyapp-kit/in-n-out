"""
these tests aren't actually executed.  They are passed to mypy.
Use the following "assertion" comments

# N: <msg> - we expect a mypy note message
# W: <msg> - we expect a mypy warning message
# E: <msg> - we expect a mypy error message
# R: <msg> - we expect a mypy note message Revealed type is '<msg>'
"""

import pytest

import in_n_out as ino

# flake8: noqa
# fmt: off



@pytest.mark.mypy_testing
def mypy_test_injection() -> None:

    def f(x: int) -> int:
        raise ValueError()

    f()  # E: Missing positional argument "x" in call to "f"  [call-arg]

    deco = ino.inject(providers=True, processors=True)
    reveal_type(deco)  # R: def [P, R] (def (*P.args, **P.kwargs) -> R`-2) -> def (*Any, **Any) -> R`-2

    injected = deco(f)
    reveal_type(injected)  # R: def (*Any, **Any) -> builtins.int

    injected()  # no error
    injected(1)

    # unfortunately, the best we can do is convert the signature to Callabe[..., R]
    # so we lose the parameter information.  but it seems better than having
    # "missing positional args" errors everywhere on injected functions.
    injected(1, 2)


@pytest.mark.mypy_testing
def mypy_test_provider() -> None:
    store = ino.Store('name')

    def func1(x: str) -> int:
        ...

    # func1 requires an argument, and so cannot be a provider
    outfunc1 = ino.mark_provider(func1)  # E: Value of type variable "ProviderVar" of "mark_provider" cannot be "Callable[[str], int]"  [type-var]
    ino.register_provider(func1)  # E: Argument 1 to "register_provider" has incompatible type "Callable[[str], int]"; expected "Callable[[], Any]"  [arg-type]
    ino.register(providers=[(func1,)])  # E: List item 0 has incompatible type "Tuple[Callable[[str], int]]"; expected "Union[Tuple[Callable[[], Any]], Tuple[Callable[[], Any], object], Tuple[Callable[[], Any], object, float]]"  [list-item]

    # works also with store methods
    store.mark_provider(func1)  # E: Value of type variable "ProviderVar" of "mark_provider" of "Store" cannot be "Callable[[str], int]"  [type-var]
    store.register_provider(func1)  # E: Argument 1 to "register_provider" of "Store" has incompatible type "Callable[[str], int]"; expected "Callable[[], Any]"  [arg-type]
    store.register(providers=[(func1,)])  # E: List item 0 has incompatible type "Tuple[Callable[[str], int]]"; expected "Union[Tuple[Callable[[], Any]], Tuple[Callable[[], Any], object], Tuple[Callable[[], Any], object, float]]"  [list-item]

    def func2() -> int:
        ...

    outfunc2 = ino.mark_provider(func2)  # func2 is fine

    # make sure decorators didn't ruin types of decorated funcs
    reveal_type(outfunc1)  # R: def (x: builtins.str) -> builtins.int
    reveal_type(outfunc2)  # R: def () -> builtins.int


@pytest.mark.mypy_testing
def mypy_test_processor() -> None:
    store = ino.Store('name')

    def func1() -> int:
        ...

    # func1 takes no arguments, and so cannot be a processor
    outfunc1 = ino.mark_processor(func1)  # E: Value of type variable "ProcessorVar" of "mark_processor" cannot be "Callable[[], int]"  [type-var]
    ino.register_processor(func1)  # E: Argument 1 to "register_processor" has incompatible type "Callable[[], int]"; expected "Callable[[Any], Any]"  [arg-type]
    ino.register(processors=[(func1,)])  # E: List item 0 has incompatible type "Tuple[Callable[[], int]]"; expected "Union[Tuple[Callable[[Any], Any]], Tuple[Callable[[Any], Any], object], Tuple[Callable[[Any], Any], object, float]]"  [list-item]

    # works also with store methods
    store.mark_processor(func1)  # E: Value of type variable "ProcessorVar" of "mark_processor" of "Store" cannot be "Callable[[], int]"  [type-var]
    store.register_processor(func1)  # E: Argument 1 to "register_processor" of "Store" has incompatible type "Callable[[], int]"; expected "Callable[[Any], Any]"  [arg-type]
    store.register(processors=[(func1,)])  # E: List item 0 has incompatible type "Tuple[Callable[[], int]]"; expected "Union[Tuple[Callable[[Any], Any]], Tuple[Callable[[Any], Any], object], Tuple[Callable[[Any], Any], object, float]]"  [list-item]

    def func2(x: int) -> int:
        ...

    outfunc2 = ino.mark_processor(func2)  # func2 is fine

    # make sure decorators didn't ruin types of decorated funcs
    reveal_type(outfunc1)  # R: def () -> builtins.int
    reveal_type(outfunc2)  # R: def (x: builtins.int) -> builtins.int
