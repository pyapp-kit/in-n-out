from typing import Optional, Sequence

import pytest

from in_n_out import Store, iter_providers, provider, set_providers

glb = Store.get_store()


def test_provider_resolution():
    with set_providers(
        [
            (Optional[int], lambda: None),
            (Optional[int], lambda: 2),
            (int, lambda: 1),
        ]
    ):
        assert glb.provide(Optional[int]) == 2


@pytest.mark.parametrize(
    "type, provide, ask_type, expect",
    [
        (int, lambda: 1, int, 1),  # provider can be a function
        (int, 1, int, 1),  # or a constant value
        (Sequence, [], list, []),  # we can ask for a subclass of a provided types
    ],
)
def test_set_providers(test_store: Store, type, provide, ask_type, expect):
    """Test that we can set provider as either function or constant, and get it back."""
    assert not test_store.provide(ask_type)
    with set_providers({type: provide}, store=test_store):
        assert test_store.provide(ask_type) == expect
    assert not test_store.provide(ask_type)  # make sure context manager cleaned up


def test_provider_decorator(test_store: Store):
    """Test the @provider decorator."""
    assert not test_store.provide(int)

    @test_store.provider
    def provides_int() -> int:
        return 1

    assert next(iter_providers(int, store=test_store)) is provides_int
    assert test_store.provide(int) == 1

    test_store.clear()
    assert not test_store.provide(int)


def test_optional_providers(test_store: Store):
    """Test providing & getting Optional[type]."""
    assert not list(test_store.iter_providers(Optional[int]))
    assert not list(test_store.iter_providers(str))

    @test_store.provider
    def provides_optional_int() -> Optional[int]:
        return 1

    @test_store.provider
    def provides_str() -> str:
        return "hi"

    assert test_store.provide(int) == 1
    # just an optional one
    assert next(test_store.iter_providers(Optional[int])) is provides_optional_int

    # but provides_str returns a string
    assert next(test_store.iter_providers(str)) is provides_str
    # which means it also provides an Optional[str]
    assert next(test_store.iter_providers(Optional[str])) is provides_str

    # also register a provider for int
    @test_store.provider(weight=10)
    def provides_int() -> int:
        return 1

    assert next(test_store.iter_providers(int)) is provides_int
    # the definite provider takes precedence
    # TODO: consider this...
    assert next(test_store.iter_providers(Optional[int])) is provides_int

    test_store.clear()

    # all clear
    assert not test_store._processors
    assert not test_store._providers


def test_unlikely_provider():
    with pytest.warns(UserWarning, match="has no return type hint"):

        @provider
        def provides_int():
            ...
