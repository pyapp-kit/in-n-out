"""pluggable dependency injection and result processing.

Generally speaking, providers and processors are defined as follows:

- `Provider: TypeAlias = Callable[[], Any]`: a callable that can accept no arguments and
  returns an instance of some type.  When we refer to a
- `Processor: TypeAlias = Callable[[Any], Any]`: a callable that accepts a single
  positional argument (an instance of some type) and returns anything (the return
  value is ignored).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("in-n-out")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "uninstalled"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from ._global import (
    inject,
    inject_processors,
    iter_processors,
    iter_providers,
    mark_processor,
    mark_provider,
    process,
    provide,
    register,
    register_processor,
    register_provider,
)
from ._store import Store
from ._type_resolution import (
    resolve_single_type_hints,
    resolve_type_hints,
    type_resolved_signature,
)
from ._util import _compiled

__all__ = [
    "Store",
    "_compiled",
    "inject",
    "inject_processors",
    "iter_processors",
    "iter_providers",
    "mark_processor",
    "mark_provider",
    "process",
    "provide",
    "register",
    "register",
    "register_processor",
    "register_provider",
    "resolve_single_type_hints",
    "resolve_type_hints",
    "type_resolved_signature",
]
