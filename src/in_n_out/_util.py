import contextlib
from typing import Any, List, Set, Tuple, Type, Union, get_origin

try:
    import cython
except ImportError:  # pragma: no cover
    _compiled: bool = False
else:  # pragma: no cover
    try:
        _compiled = cython.compiled
    except AttributeError:
        _compiled = False


UNION_TYPES: Set[Any] = {Union}

with contextlib.suppress(ImportError):
    from types import UnionType

    UNION_TYPES.add(UnionType)


def _is_union(type_: Any) -> bool:
    return get_origin(type_) in UNION_TYPES


def _split_union(type_: Any) -> Tuple[List[Type], bool]:
    optional = False
    if _is_union(type_):
        types = []
        for arg in getattr(type_, "__args__", ()):
            if arg is type(None):  # noqa: E721
                optional = True
            else:
                types.append(arg)
    else:
        types = [type_]
    return types, optional


def issubclassable(obj: Any) -> bool:
    """Return True if `obj` can be used as the second argument in issubclass."""
    try:
        issubclass(type, obj)
        return True
    except TypeError:
        return False
