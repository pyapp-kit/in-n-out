from typing import Iterator

import pytest

from in_n_out._store import Store


@pytest.fixture
def test_store() -> Iterator[Store]:
    try:
        yield Store.create("test")
    finally:
        Store.destroy("test")


@pytest.fixture(autouse=True)
def clear_global_store():
    yield
    Store.get_store().clear()
