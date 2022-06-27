try:
    import cython
except ImportError:  # pragma: no cover
    _compiled: bool = False
else:  # pragma: no cover
    try:
        _compiled = cython.compiled
    except AttributeError:
        _compiled = False
