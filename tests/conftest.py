import pytest

from in_n_out._store import Store


@pytest.fixture
def test_store():

    store = Store.create("test")
    try:
        yield store
    finally:
        Store.destroy("test")


# @pytest.fixture(autouse=True)
# def _clean_store():
#     yield
#     Store.get_store().clear()
