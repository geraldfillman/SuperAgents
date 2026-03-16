"""MiroFish simulation runtime integration."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

_RUNTIME_EXPORTS = {
    "MIROFISH_HOME_ENV",
    "check_runtime",
    "launch_simulation",
    "resolve_runtime_home",
}
_STATUS_EXPORTS = {
    "read_runtime_status",
    "send_close_command",
}
_BUNDLE_EXPORTS = {
    "MiroFishAgentProfile",
    "MiroFishBundleSpec",
    "create_bundle_from_spec",
    "load_bundle_spec",
    "read_bundle",
}
_ZEP_EXPORTS = {
    "build_bundle_import_manifest",
    "publish_bundle_to_zep",
    "register_bundle_import",
    "summarize_bundle_activity",
}

__all__ = sorted(_RUNTIME_EXPORTS | _STATUS_EXPORTS | _BUNDLE_EXPORTS | _ZEP_EXPORTS)

if TYPE_CHECKING:
    from .bundle import (
        MiroFishAgentProfile,
        MiroFishBundleSpec,
        create_bundle_from_spec,
        load_bundle_spec,
        read_bundle,
    )
    from .runtime import MIROFISH_HOME_ENV, check_runtime, launch_simulation, resolve_runtime_home
    from .status import read_runtime_status, send_close_command
    from .zep import (
        build_bundle_import_manifest,
        publish_bundle_to_zep,
        register_bundle_import,
        summarize_bundle_activity,
    )


def __getattr__(name: str):
    if name in _RUNTIME_EXPORTS:
        module = import_module(".runtime", __name__)
    elif name in _STATUS_EXPORTS:
        module = import_module(".status", __name__)
    elif name in _BUNDLE_EXPORTS:
        module = import_module(".bundle", __name__)
    elif name in _ZEP_EXPORTS:
        module = import_module(".zep", __name__)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    value = getattr(module, name)
    globals()[name] = value
    return value
