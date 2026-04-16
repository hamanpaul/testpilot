# TestPilot Versioning and Release Flow

This document defines the repository-level versioning and release process for
TestPilot starting from the existing tag baseline `v0.1.5`.

## 1. Versioning policy

TestPilot uses Semantic Versioning with git tags in the form `vX.Y.Z`.

- **Major (`X`)**: breaking operator-facing or consumer-facing changes
  (CLI contract breaks, artifact layout breaks, report format removals, or
  incompatible workflow changes).
- **Minor (`Y`)**: backward-compatible features (new commands, new reporting
  capabilities, new plugin/runtime features, new supported workflows).
- **Patch (`Z`)**: backward-compatible fixes, documentation corrections, test
  improvements, and release automation maintenance.

`v0.1.5` is the starting baseline for this formalized process.

## 2. Canonical version sources

- **Canonical source**: `pyproject.toml` → `[project].version`
- **Runtime mirror**: `src/testpilot/__init__.py` → `__version__`
- **Published identifier**: git tag `vX.Y.Z`

All three must agree for a release. The repo test suite includes a guardrail to
catch drift between `pyproject.toml` and `src/testpilot/__init__.py`, and the
release workflow validates that the pushed tag matches the in-repo version.

## 3. Day-to-day pull request expectations

Normal feature/fix branches continue to merge through GitHub pull requests.

Each PR should use the GitHub PR template and explicitly cover:

- whether `CHANGELOG.md` needs an `Unreleased` entry
- whether README / docs / AGENTS updates are required
- what validation was run
- whether the change has release-note impact

Rule of thumb:

- **User-facing or operator-facing changes**: update `CHANGELOG.md`
- **Purely internal churn with no release-note value**: explain why changelog is
  not needed in the PR

## 4. Release preparation flow

Prepare releases in a dedicated branch and PR:

1. Branch from `main` as `release/vX.Y.Z`.
2. Update `pyproject.toml` and `src/testpilot/__init__.py` to `X.Y.Z`.
3. Finalize `CHANGELOG.md`:
   - keep a fresh `Unreleased` section at the top
   - move release-ready notes into `## [X.Y.Z]`
4. Update `README.md`, `docs/release-flow.md`, and `AGENTS.md` if the release
   changes supported workflows, release rules, or operator guidance.
5. Ensure CI is green and any release-specific checks are complete.
6. Merge the release PR into `main`.

Recommended PR title:

- `release: prepare vX.Y.Z`

## 5. Tagging and publication

After the release PR is merged:

1. Create git tag `vX.Y.Z` on the merged `main` commit.
2. Push the tag (or create it from GitHub on the target commit).
3. The tag push triggers `.github/workflows/release.yml`.
4. The workflow:
   - verifies tag/version consistency
   - creates the GitHub Release
   - uses GitHub auto-generated release notes for the published release page

GitHub Releases are the canonical published release notes surface. `CHANGELOG.md`
remains the curated in-repo history.

## 6. Release gates

Do not tag a release until all of the following are true:

- the release PR is merged into `main`
- GitHub Actions CI is green for the release commit
- `pyproject.toml`, `src/testpilot/__init__.py`, and the intended tag match
- `CHANGELOG.md` is finalized
- README / docs / AGENTS updates are merged when user-facing behavior changed

At the moment, the minimum automated CI gate is the repo test suite
(`uv run pytest -q`) via GitHub Actions.

## 7. Hotfixes

Hotfix releases follow the same flow with a patch bump:

1. branch from `main`
2. fix the issue
3. prepare the next patch release PR (for example `release/v0.1.6`)
4. merge
5. tag the merged commit

## 8. Recovery when a tag is wrong

If a tag is pushed with the wrong version:

1. delete the incorrect GitHub Release (if it was created)
2. delete the incorrect git tag
3. fix version metadata / changelog on a new PR
4. retag the correct merged `main` commit

Do not reuse an incorrect tag name for a different commit without first
cleaning up the bad release/tag state.
