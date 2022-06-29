import pytest

from in_n_out import Store
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
