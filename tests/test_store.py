from typing import Optional

import pytest

from in_n_out import Store, inject_dependencies, provider, set_processors, set_providers
from in_n_out._store import _GLOBAL


def test_create_get_destroy():
    assert len(Store._instances) == 1
    assert Store.get_store().name == _GLOBAL

    name = "test"

    test_store = Store.create(name)
    assert test_store is Store.get_store(name)
    assert len(Store._instances) == 2

    with pytest.raises(KeyError, match=f"Store {name!r} already exists"):
        Store.create(name)

    Store.destroy(name)
    assert len(Store._instances) == 1

    with pytest.raises(KeyError, match=f"Store {name!r} does not exist"):
        Store.get_store(name)

    with pytest.raises(KeyError, match=f"Store {name!r} does not exist"):
        Store.destroy(name)

    with pytest.raises(ValueError, match="The global store cannot be destroyed"):
        Store.destroy(_GLOBAL)

    with pytest.raises(KeyError, match=f"{_GLOBAL!r} is a reserved store name"):
        Store.create(_GLOBAL)

    assert len(Store._instances) == 1


def test_store_clear(test_store: Store):

    assert not test_store._providers
    assert not test_store._processors

    set_providers({int: 1}, store=test_store)
    set_providers({Optional[str]: None}, store=test_store)
    set_processors({int: print}, store=test_store)
    assert len(test_store._providers) == 2
    assert len(test_store._processors) == 1

    test_store.clear()
    assert not test_store._providers
    assert not test_store._processors


def test_store_namespace(test_store: Store):
    class T:
        ...

    @provider(store=test_store)
    def provide_t() -> T:
        return T()

    # namespace can be a static dict
    test_store.namespace = {"Hint": T}

    @inject_dependencies(store=test_store)
    def use_t(t: "Hint") -> None:  # type: ignore  # noqa: F821
        return t

    assert isinstance(use_t(), T)

    # namespace can also be a callable
    test_store.namespace = lambda: {"Hint2": T}

    @inject_dependencies(store="test")
    def use_t2(t: "Hint2") -> None:  # type: ignore  # noqa: F821
        return t

    assert isinstance(use_t2(), T)
