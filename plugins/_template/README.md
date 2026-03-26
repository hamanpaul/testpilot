# Plugin Template

Copy this directory to create a new TestPilot plugin:

```bash
cp -r plugins/_template plugins/my_plugin
```

Then edit:
1. `plugin.py` — implement the 8 abstract methods from `PluginBase`
2. `cases/*.yaml` — define your test cases
3. Optionally add `agent-config.yaml` for runner/agent policy

## Required PluginBase Methods

| Method | Purpose |
|--------|---------|
| `name` | Plugin identifier (e.g., `"my_plugin"`) |
| `version` | Semantic version string |
| `discover_cases()` | Scan `cases/` directory for YAML test cases |
| `setup_env()` | Provision DUT/STA/endpoint for a test case |
| `verify_env()` | Validate environment readiness |
| `execute_step()` | Run a single test step via transport |
| `evaluate()` | Check pass criteria against step results |
| `teardown()` | Clean up after test case |
