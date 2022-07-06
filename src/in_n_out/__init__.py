"""plugable dependency injection and result processing."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("in-n-out")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "uninstalled"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from ._global import (
    inject_dependencies,
    iter_processors,
    iter_providers,
    process,
    process_output,
    processor,
    provide,
    provider,
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
    "register_provider",
    "_compiled",
    "inject_dependencies",
    "iter_processors",
    "iter_providers",
    "process_output",
    "process",
    "processor",
    "provide",
    "provider",
    "register_processor",
    "register",
    "register",
    "resolve_single_type_hints",
    "resolve_type_hints",
    "Store",
    "type_resolved_signature",
]
