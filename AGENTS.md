# TestPilot Development Guidelines

## Project Structure

```
src/testpilot/       # Core engine (Python 3.11+)
  core/              # orchestrator, plugin_base, plugin_loader, testbed_config
  transport/         # serial, adb, ssh, network (TransportBase ABC)
  env/               # topology, provisioner, validator
  schema/            # YAML case schema validation
plugins/             # Test plugins (each dir = one plugin)
configs/             # Testbed YAML configs
```

## Commands

```bash
uv pip install -e ".[dev]"     # Install with dev deps
testpilot --version            # Check version
testpilot list-plugins         # Discover plugins
testpilot list-cases <plugin>  # List test cases
testpilot run <plugin>         # Run tests
pytest                         # Run unit tests
ruff check src/ plugins/       # Lint
```

## Code Style

- Python 3.11+, type hints mandatory
- Minimal inline comments (for maintainers, not tutorials)
- Follow existing naming conventions
- Plugin interface: inherit `PluginBase`, export as `Plugin` class
- Transport interface: inherit `TransportBase`
- Test cases: YAML descriptors in `plugins/<name>/cases/`

## Plugin Development

1. Create `plugins/<name>/plugin.py` with `class Plugin(PluginBase)`
2. Create `plugins/<name>/cases/*.yaml` for test items
3. Implement all `PluginBase` abstract methods
4. Plugin is auto-discovered by `PluginLoader`

## Key Conventions

- Testbed config: `configs/testbed.yaml`
- Variable substitution: `{{VAR_NAME}}` in YAML resolved from testbed.variables
- Reports output to `reports/` (gitignored)
- All paths use absolute references internally
