from typing import Generic, List, Optional, Sequence, TypeVar, Union
from unittest.mock import Mock

import pytest

from in_n_out import Store, iter_processors, processor, set_processors

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
def test_set_processors(test_store: Store, type, process, ask_type):
    """Test that we can set processor as function or constant, and get it back."""
    assert not list(test_store.iter_processors(ask_type))
    with set_processors({type: process}, store=test_store):
        assert list(test_store.iter_processors(type))
        assert list(test_store.iter_processors(ask_type))
        MOCK.reset_mock()
        test_store.process(ask_type, 1)
        MOCK.assert_called_once()
    assert not list(
        test_store.iter_processors(ask_type)
    )  # make sure context manager cleaned up
    assert len(test_store._processors) == 0


def test_set_processors_cleanup(test_store: Store):
    """Test that we can set processors in contexts, and cleanup"""
    assert not list(test_store.iter_processors(int))
    mock = Mock()
    mock2 = Mock()
    with set_processors({int: lambda v: mock(v)}, store=test_store):
        assert len(test_store._processors) == 1
        test_store.process(int, 2)
        mock.assert_called_once_with(2)
        mock.reset_mock()

        with set_processors([(int, lambda x: mock2(x * x), 10)], store=test_store):
            assert len(test_store._processors) == 2
            test_store.process(int, 2, first_processor_only=True)
            mock2.assert_called_once_with(4)
            mock.assert_not_called()
            mock2.reset_mock()

        assert len(test_store._processors) == 1
        test_store.process(int, 2)
        mock.assert_called_once_with(2)
        mock2.assert_not_called()

    assert not list(test_store.iter_processors(int))


def test_processor_decorator(test_store: Store):
    """Test the @processor decorator."""
    assert not list(test_store.iter_processors(int))

    @test_store.processor
    def processes_int(x: int):
        ...

    assert next(test_store.iter_processors(int)) is processes_int

    test_store.clear()
    assert not list(test_store.iter_processors(int))


def test_optional_processors(test_store: Store):
    """Test processing Optional[type]."""
    assert not list(test_store.iter_processors(Optional[int]))
    assert not list(test_store.iter_processors(str))

    @processor(store=test_store)
    def processes_int(x: int):
        return 1

    @test_store.processor  # these decorators are equivalent
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

    assert next(iter_processors(int, store=test_store)) is processes_int
    # the definite processor takes precedence
    # TODO: consider this...
    assert next(test_store.iter_processors(Optional[int])) is processes_int


def test_union_processors(test_store: Store):
    @test_store.processor
    def processes_int_or_str(x: Union[int, str]):
        return 1

    assert next(test_store.iter_processors(int)) is processes_int_or_str
    assert next(test_store.iter_processors(str)) is processes_int_or_str


def test_unlikely_processor():
    with pytest.warns(UserWarning, match="has no argument type hints"):

        @processor
        def provides_int():
            ...

    with pytest.raises(ValueError, match="Processors must take at least one argument"):
        set_processors({int: lambda: 1})

    with pytest.raises(ValueError, match="Processors must be callable"):
        set_processors({int: 1})


def test_no_generics():
    T = TypeVar("T")

    class G(Generic[T]):
        ...

    # parametrized generics not yet supported
    with pytest.raises(TypeError, match="cannot be used as a processor"):

        @processor
        def _(x: List[int]):
            ...

    with pytest.raises(TypeError, match="cannot be used as a processor"):

        @processor
        def _(x: G[int]):
            ...

    # but ok without params
    @processor
    def _(x: List):
        ...

    @processor
    def _(x: G):
        ...
