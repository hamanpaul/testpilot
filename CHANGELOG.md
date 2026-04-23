# Changelog

All notable changes to this project are documented in this file.

TestPilot follows Semantic Versioning (`vX.Y.Z`). GitHub Releases publish the
auto-generated release notes for each tag, while this file keeps the curated
repo changelog and the `Unreleased` queue that must be finalized during release
preparation.

## [Unreleased]

### Added

- `testpilot run wifi_llapi` now performs a runtime alignment phase that
  auto-corrects case filename `D###`, `source.row`, and compatible `id` values
  against the checked-in template workbook before execution.
- wifi_llapi artifact bundles may now include `blocked_cases.md` and
  `skipped_cases.md` when metadata drift cannot be safely auto-aligned.

### Changed - BREAKING

- `testpilot run wifi_llapi` no longer accepts `--report-source-xlsx`; rebuild the checked-in template with `testpilot wifi-llapi build-template-report --source-xlsx <path>` before running if the template needs refreshing.

### Removed - BREAKING

- `plugins/wifi_llapi/cases/` no longer carries `results_reference`, `source.baseline`,
  `source.report`, or `source.sheet`; wifi_llapi report values now reflect runtime
  verdicts instead of workbook-derived oracle metadata.
- `testpilot.core.case_utils.baseline_results_reference()` has been removed;
  `case_band_results()` now projects per-band results from runtime verdict plus
  `case.bands` only.

## [0.2.0]

### Added

- Per-run wifi_llapi artifact bundles under `plugins/wifi_llapi/reports/<artifact_name>/`
  that keep xlsx, markdown, json, UART logs, trace output, and optional
  alignment warnings together.
- Local HTML diagnostic report generation from existing JSON run artifacts,
  including Arcadyan-styled case details.
- GitHub-native release management scaffolding: PR template checklist, CI
  workflow, tag-triggered release publishing, and release process
  documentation.

### Changed

- Report and template handling now use portable manifest paths and aligned repo
  documentation for the current autopilot / reporting architecture.
- Local workbook / compare outputs and one-off campaign notes are now treated as
  local-only artifacts instead of versioned repo content.
- Version metadata is now promoted from the historical `v0.1.5` baseline to the
  release target `v0.2.0`.

### Fixed

- Markdown reports now include the full statistics block expected by downstream
  review flows.
- HTML case details now render referenced DUT / STA log snippets with readable
  truncation for large ranges.
- 6G DUT runtime cleanup now preserves non-ASCII output safely during case
  execution.

## [0.1.5]

### Note

- Historical baseline release that predates formal changelog maintenance in
  this repository. Future curated changelog entries build forward from this
  tag.
