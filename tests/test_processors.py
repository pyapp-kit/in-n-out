from typing import Optional, Sequence, Union
from unittest.mock import Mock

import pytest

import in_n_out as ino

R = object()

MOCK = Mock()


@pytest.mark.parametrize(
    "type, process, ask_type",
    [
        (int, lambda x: MOCK(), int),  # processor can be a function
        # we can ask for a subclass of a provided types
        (Sequence, lambda x: MOCK(), list),
        (Union[list, tuple], lambda x: MOCK(), tuple),
        (Union[list, tuple], lambda x: MOCK(), list),
    ],
)
def test_set_processors(type, process, ask_type):
    """Test that we can set processor as function or constant, and get it back."""
    assert not list(ino.iter_processors(ask_type))
    with ino.register(processors={type: process}):
        assert list(ino.iter_processors(type))
        assert list(ino.iter_processors(ask_type))
        MOCK.reset_mock()
        ino.process(1, type_hint=ask_type)
        MOCK.assert_called_once()
    # make sure context manager cleaned up
    assert not list(ino.iter_processors(ask_type))


def test_set_processors_cleanup(test_store: ino.Store):
    """Test that we can set processors in contexts, and cleanup"""
    assert not list(test_store.iter_processors(int))
    mock = Mock()
    mock2 = Mock()
    with test_store.register(processors={int: lambda v: mock(v)}):
        assert len(test_store._processors) == 1
        test_store.process(2)
        mock.assert_called_once_with(2)
        mock.reset_mock()

        with test_store.register(processors=[(lambda x: mock2(x * x), int, 10)]):
            assert len(test_store._processors) == 2
            test_store.process(2, first_processor_only=True)
            mock2.assert_called_once_with(4)
            mock.assert_not_called()
            mock2.reset_mock()

        assert len(test_store._processors) == 1
        test_store.process(2)
        mock.assert_called_once_with(2)
        mock2.assert_not_called()

    assert not list(test_store.iter_processors(int))


def test_processor_decorator(test_store: ino.Store):
    """Test the @processor decorator."""
    assert not list(test_store.iter_processors(int))

    @test_store.mark_processor
    def processes_int(x: int):
        ...

    assert next(test_store.iter_processors(int)) is processes_int

    test_store.clear()
    assert not list(test_store.iter_processors(int))


def test_optional_processors(test_store: ino.Store):
    """Test processing Optional[type]."""
    assert not list(test_store.iter_processors(Optional[int]))
    assert not list(test_store.iter_processors(str))

    @test_store.mark_processor
    def processes_int(x: int):
        return 1

    @test_store.mark_processor  # these decorators are equivalent
    def processes_string(x: str):
        ...

    # we don't have a processor guaranteed to take an int
    # assert not get_processor(int)
    # just an optional one
    assert next(test_store.iter_processors(Optional[int])) is processes_int

    # but processes_string takes a string
    assert next(test_store.iter_processors(str)) is processes_string
    # which means it also provides an Optional[str]
    assert next(test_store.iter_processors(Optional[str])) is processes_string

    assert next(test_store.iter_processors(int)) is processes_int
    # the definite processor takes precedence
    # TODO: consider this...
    assert next(test_store.iter_processors(Optional[int])) is processes_int


def test_union_processors(test_store: ino.Store):
    @test_store.mark_processor
    def processes_int_or_str(x: Union[int, str]):
        return 1

    assert next(test_store.iter_processors(int)) is processes_int_or_str
    assert next(test_store.iter_processors(str)) is processes_int_or_str


def test_unlikely_processor():
    with pytest.warns(UserWarning, match="has no argument type hints"):

        @ino.mark_processor
        def provides_int():
            ...

    with pytest.raises(ValueError, match="Processors must take at least one argument"):
        ino.register(processors={int: lambda: 1})

    with pytest.raises(ValueError, match="Processors must be callable"):
        ino.register(processors={int: 1})


def test_global_register():
    mock = Mock()

    def f(x: int):
        mock(x)

    ino.register_processor(f)
    ino.process(1)
    mock.assert_called_once_with(1)


def test_processor_provider_recursion() -> None:
    """Make sure to avoid infinte recursion when a provider uses processors."""

    class Thing:
        count = 0

    # this is both a processor and a provider
    @ino.register_provider
    @ino.inject_processors
    def thing_provider() -> Thing:
        return Thing()

    @ino.inject
    def add_item(thing: Thing) -> None:
        thing.count += 1

    N = 3
    for _ in range(N):
        ino.register_processor(add_item)

    @ino.inject
    def func(thing: Thing) -> int:
        return thing.count

    assert func() == N
