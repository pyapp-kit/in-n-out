import pytest


@pytest.fixture
def test_store():
    from in_n_out._store import Store

    store = Store.create("test")
    try:
        yield store
    finally:
        Store.destroy("test")
