from typing import Optional, Sequence

import pytest

from in_n_out import Store, get_provider, provider, set_providers
from in_n_out._providers import clear_provider
from in_n_out._store import _GLOBAL


@pytest.mark.parametrize(
    "type, provide, ask_type, expect",
    [
        (int, lambda: 1, int, 1),  # provider can be a function
        (int, 1, int, 1),  # or a constant value
        (Sequence, [], list, []),  # we can ask for a subclass of a provided types
    ],
)
def test_set_providers(type, provide, ask_type, expect):
    """Test that we can set provider as either function or constant, and get it back."""
    assert not get_provider(ask_type)
    with set_providers({type: provide}):
        assert get_provider(ask_type)() == expect
    assert not get_provider(ask_type)  # make sure context manager cleaned up


def test_set_providers_cleanup():
    """Test that we can set providers in contexts, and cleanup"""
    assert not get_provider(int)

    with set_providers({int: 1}):
        assert get_provider(int)() == 1
        with pytest.raises(ValueError, match="already has a provider and 'clobber' is"):
            set_providers({int: 2})
        with set_providers({int: 2}, clobber=True):
            assert get_provider(int)() == 2
        assert get_provider(int)() == 1

    assert not get_provider(int)


def test_provider_decorator():
    """Test the @provider decorator."""
    assert not get_provider(int)

    @provider
    def provides_int() -> int:
        return 1

    assert get_provider(int) is provides_int
    assert get_provider(int)() == 1

    clear_provider(int)
    assert not get_provider(int)

    with pytest.warns(UserWarning, match="No provider was registered"):
        clear_provider(int, warn_missing=True)


def test_optional_providers():
    """Test providing & getting Optional[type]."""
    assert not get_provider(Optional[int])
    assert not get_provider(str)

    @provider
    def provides_optional_int() -> Optional[int]:
        return 1

    @provider
    def provides_str() -> str:
        return "hi"

    # we don't have a provider guaranteed to return an int
    assert not get_provider(int)
    # just an optional one
    assert get_provider(Optional[int]) is provides_optional_int

    # but provides_str returns a string
    assert get_provider(str) is provides_str
    # which means it also provides an Optional[str]
    assert get_provider(Optional[str]) is provides_str

    # also register a provider for int
    @provider
    def provides_int() -> int:
        return 1

    assert get_provider(int) is provides_int
    # the definite provider takes precedence
    # TODO: consider this...
    assert get_provider(Optional[int]) is provides_int

    # TODO: consider this
    # when clearing `int` would get rid of `provides_optional_int` AND `provides_int`
    # but clearing Optional[int] would only get rid of `provides_optional_int`
    assert clear_provider(Optional[int]) is provides_optional_int
    assert clear_provider(int) is provides_int
    assert clear_provider(str) is provides_str

    # all clear
    assert not Store.get_store(_GLOBAL).opt_providers
    assert not Store.get_store(_GLOBAL).providers


def test_unlikely_provider():
    with pytest.warns(UserWarning, match="has no return type hint"):

        @provider
        def provides_int():
            ...
