from collections import ChainMap
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    NewType,
    Sequence,
    Set,
    TypeVar,
)
from unittest.mock import Mock

import pytest

if TYPE_CHECKING:
    from in_n_out import Store

T = TypeVar("T")


class G(Generic[T]):
    ...


nt = NewType("nt", int)
NON_SUBCLASSABLE_TYPES = ["hi", nt, List[nt], T, Callable[[int], str], G[int]]
SUBCLASS_PAIRS = [
    (list, Sequence),
    (tuple, Sequence),
    (dict, Mapping),
    (set, Set),
    (list, Iterable),
    (ChainMap, MutableMapping),
]


@pytest.mark.parametrize("type_", NON_SUBCLASSABLE_TYPES)
@pytest.mark.parametrize("mode", ["provider", "processor"])
def test_non_standard_types(test_store: "Store", type_, mode) -> None:
    mock = Mock(return_value=1)
    if mode == "provider":
        test_store.register_provider(mock, type_)
        assert test_store.provide(type_) == 1
        mock.assert_called_once()
    else:
        test_store.register_processor(mock, type_)
        test_store.process(2, type_hint=type_)
        mock.assert_called_once_with(2)


def test_provider_type_error(test_store: "Store") -> None:
    with pytest.raises(TypeError, match="cannot be used as a provider hint"):
        test_store.register_provider(lambda: 1, set())
    with pytest.raises(TypeError, match="cannot be used as a processor hint"):
        test_store.register_processor(lambda x: None, set())


@pytest.mark.parametrize("sub, sup", SUBCLASS_PAIRS)
@pytest.mark.parametrize("mode", ["provider", "processor"])
def test_subclass_pairs(test_store: "Store", sub, sup, mode) -> None:
    mock = Mock(return_value=1)
    if mode == "provider":
        test_store.register_provider(mock, sup)
        assert test_store.provide(sub) == 1
        mock.assert_called_once()
    else:
        test_store.register_processor(mock, sup)
        test_store.process(2, type_hint=sub)
        mock.assert_called_once_with(2)

    test_store.clear()
    mock.reset_mock()
    if mode == "provider":
        test_store.register_provider(sub, mock)
        assert test_store.provide(sup) is None
    else:
        test_store.register_processor(sub, mock)
        test_store.process(2, type_hint=sup)
    mock.assert_not_called()
