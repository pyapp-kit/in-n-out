"""plugable dependency injection and result processing."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("in-n-out")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "uninstalled"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from ._inject import inject_dependencies
from ._processors import iter_processors, processor, set_processors
from ._providers import iter_providers, provider, set_providers
from ._store import Store
from ._type_resolution import (
    resolve_single_type_hints,
    resolve_type_hints,
    type_resolved_signature,
)
from ._util import _compiled

__all__ = [
    "_compiled",
    "iter_processors",
    "iter_providers",
    "inject_dependencies",
    "processor",
    "provider",
    "resolve_single_type_hints",
    "resolve_type_hints",
    "set_processors",
    "set_providers",
    "Store",
    "type_resolved_signature",
]
