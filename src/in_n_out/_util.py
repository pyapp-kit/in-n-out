import types
from typing import Any, List, Set, Tuple, Type, Union, cast, get_origin

_compiled: bool = False


UNION_TYPES: Set[Any] = {Union}
if hasattr(types, "UnionType"):
    # doing it this way to deal with python-version specific linting issues
    UNION_TYPES.add(cast(Any, getattr(types, "UnionType")))  # noqa


def _is_union(type_: Any) -> bool:
    return get_origin(type_) in UNION_TYPES


def _split_union(type_: Any) -> Tuple[List[Type], bool]:
    optional = False
    if _is_union(type_):
        types = []
        for arg in getattr(type_, "__args__", ()):
            if arg is type(None):
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
