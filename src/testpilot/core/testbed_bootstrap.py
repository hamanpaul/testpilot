"""Stage a plugin's testbed template into the effective configs/testbed.yaml.

Each plugin ships its own ``plugins/<name>/testbed.yaml.example``. When the CLI
resolves a plugin context, it copies that template into ``configs/testbed.yaml``
(always overwriting) so the runtime always reads a testbed shaped for the
plugin currently being run, with no leakage between plugins.
"""
from __future__ import annotations

import shutil
from pathlib import Path

PLUGIN_TESTBED_TEMPLATE = "testbed.yaml.example"
EFFECTIVE_TESTBED = "testbed.yaml"


def stage_plugin_testbed(
    plugins_dir: Path,
    plugin_name: str,
    configs_dir: Path,
) -> Path:
    """Copy ``plugins/<plugin_name>/testbed.yaml.example`` to ``configs/testbed.yaml``.

    Always overwrites the destination so switching between plugins never
    leaves stale settings from the previous plugin's testbed.
    """
    plugin_dir = plugins_dir / plugin_name
    if not plugin_dir.is_dir():
        raise FileNotFoundError(
            f"plugin directory not found: {plugin_dir} (plugin '{plugin_name}')"
        )

    template = plugin_dir / PLUGIN_TESTBED_TEMPLATE
    if not template.is_file():
        raise FileNotFoundError(
            f"plugin '{plugin_name}' is missing {PLUGIN_TESTBED_TEMPLATE} at {template}"
        )

    configs_dir.mkdir(parents=True, exist_ok=True)
    destination = configs_dir / EFFECTIVE_TESTBED
    shutil.copyfile(template, destination)
    return destination
