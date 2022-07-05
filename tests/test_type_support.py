from collections import ChainMap
from typing import (
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
def test_non_standard_types(test_store: Store, type_, mode) -> None:
    mock = Mock(return_value=1)
    if mode == "provider":
        test_store.register_provider(type_, mock)
        assert test_store.provide(type_) == 1
        mock.assert_called_once()
    else:
        test_store.register_processor(type_, mock)
        test_store.process(type_, 2)
        mock.assert_called_once_with(2)


def test_provider_type_error(test_store: Store) -> None:
    with pytest.raises(TypeError, match="cannot be used as a provider hint"):
        test_store.register_provider(set(), lambda: 1)
    with pytest.raises(TypeError, match="cannot be used as a processor hint"):
        test_store.register_processor(set(), lambda x: None)


@pytest.mark.parametrize("sub, sup", SUBCLASS_PAIRS)
@pytest.mark.parametrize("mode", ["provider", "processor"])
def test_subclass_pairs(test_store: Store, sub, sup, mode) -> None:
    mock = Mock(return_value=1)
    if mode == "provider":
        test_store.register_provider(sup, mock)
        assert test_store.provide(sub) == 1
        mock.assert_called_once()
    else:
        test_store.register_processor(sup, mock)
        test_store.process(sub, 2)
        mock.assert_called_once_with(2)
