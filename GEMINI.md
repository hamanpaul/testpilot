# TestPilot Agent Instructions

policy_version: 1.0.1

Follow `AGENTS.md` as the canonical project-specific instruction source.

Release/install governance summary:

- Use `VERSION` as the canonical project version; keep `pyproject.toml` and
  `src/testpilot/__init__.py` synchronized.
- Prefer the managed `testpilot` command for operator workflows.
- Use `testpilot wifi_llapi` as the primary normal wifi_llapi run command;
  `testpilot run wifi_llapi` is compatibility-only.
- Keep README CLI help marker blocks declared in `.project-policy.yml` in sync
  with CLI output whenever help text changes.
- Do not commit local secrets, lab configs, workbook inputs, or runtime report
  bundles.
