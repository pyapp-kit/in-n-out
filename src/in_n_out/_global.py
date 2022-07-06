from typing import Callable, Iterable, Mapping, Union

from ._store import CallbackTuple, Store


def register(
    *,
    processors: Union[Mapping[object, Callable], Iterable[CallbackTuple], None] = None,
    providers: Union[Mapping[object, Callable], Iterable[CallbackTuple], None] = None,
    store: Union[str, Store, None] = None,
):
    _store = store if isinstance(store, Store) else Store.get_store(store)
    return _store.register(providers=providers, processors=processors)
