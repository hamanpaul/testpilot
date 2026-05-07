"""Tests for expanded _handle_verify_install checks (Task 2.3).

Focuses on:
- Version mirror mismatch → non-zero exit
- Missing skill → non-zero exit (additional variants)
- Healthy state with managed checkout → zero exit
- Managed checkout status reporting
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from testpilot.cli import _handle_verify_install


# ---------------------------------------------------------------------------
# Version mirror checks
# ---------------------------------------------------------------------------


class TestVersionMirrorCheck:
    """_handle_verify_install must exit non-zero when version files are misaligned."""

    def test_version_mismatch_fails_verify(self, tmp_path: Path) -> None:
        """VERSION differs from pyproject.toml → verify-install exits non-zero."""
        managed_src = tmp_path / "managed_src"
        managed_src.mkdir()

        (managed_src / "VERSION").write_text("0.1.0\n")
        (managed_src / "pyproject.toml").write_text(
            '[project]\nname = "testpilot"\nversion = "0.2.0"\n'
        )
        init_dir = managed_src / "src" / "testpilot"
        init_dir.mkdir(parents=True)
        (init_dir / "__init__.py").write_text('__version__ = "0.2.0"\n')

        skill_dir = tmp_path / "skills" / "testpilot-normal-test"
        skill_dir.mkdir(parents=True)

        with patch("testpilot.cli._get_managed_src", return_value=managed_src):
            with patch("testpilot.cli._get_skills_root", return_value=tmp_path / "skills"):
                with pytest.raises(SystemExit) as exc_info:
                    _handle_verify_install()
        assert exc_info.value.code != 0

    def test_malformed_pyproject_fails_verify(self, tmp_path: Path) -> None:
        """Unreadable pyproject version metadata is a hard verify-install failure."""
        managed_src = tmp_path / "managed_src"
        managed_src.mkdir()

        (managed_src / "VERSION").write_text("0.2.0\n")
        (managed_src / "pyproject.toml").write_text("[project\nversion = ")
        init_dir = managed_src / "src" / "testpilot"
        init_dir.mkdir(parents=True)
        (init_dir / "__init__.py").write_text('__version__ = "0.2.0"\n')

        skill_dir = tmp_path / "skills" / "testpilot-normal-test"
        skill_dir.mkdir(parents=True)
        managed_venv = tmp_path / ".venv"
        (managed_venv / "bin").mkdir(parents=True)
        console_script = managed_venv / "bin" / "testpilot"
        console_script.write_text("#!/usr/bin/env sh\n")
        wrapper = tmp_path / "bin" / "testpilot"
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text(f'#!/usr/bin/env sh\nexec "{console_script}" "$@"\n')

        mock_console = MagicMock()
        with patch("testpilot.cli._get_managed_src", return_value=managed_src):
            with patch("testpilot.cli._get_managed_venv", return_value=managed_venv):
                with patch("testpilot.cli._get_wrapper_path", return_value=wrapper):
                    with patch("testpilot.cli._get_skills_root", return_value=tmp_path / "skills"):
                        with patch("testpilot.cli.console", mock_console):
                            with pytest.raises(SystemExit) as exc_info:
                                _handle_verify_install()
        assert exc_info.value.code != 0
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "pyproject.toml" in output

    def test_malformed_pyproject_fails_when_it_is_only_version_source(
        self, tmp_path: Path
    ) -> None:
        """A malformed pyproject cannot be skipped just because other mirrors are absent."""
        managed_src = tmp_path / "managed_src"
        managed_src.mkdir()
        (managed_src / "pyproject.toml").write_text("[project\nversion = ")

        from testpilot.cli import _check_version_mirrors

        ok, msg = _check_version_mirrors(managed_src)

        assert not ok
        assert "pyproject.toml" in msg

    def test_version_aligned_passes(self, tmp_path: Path) -> None:
        """All version mirrors aligned → verify-install does not fail on version check."""
        managed_src = tmp_path / "managed_src"
        managed_src.mkdir()

        (managed_src / "VERSION").write_text("0.2.0\n")
        (managed_src / "pyproject.toml").write_text(
            '[project]\nname = "testpilot"\nversion = "0.2.0"\n'
        )
        init_dir = managed_src / "src" / "testpilot"
        init_dir.mkdir(parents=True)
        (init_dir / "__init__.py").write_text('__version__ = "0.2.0"\n')

        skill_dir = tmp_path / "skills" / "testpilot-normal-test"
        skill_dir.mkdir(parents=True)
        managed_venv = tmp_path / ".venv"
        (managed_venv / "bin").mkdir(parents=True)
        console_script = managed_venv / "bin" / "testpilot"
        console_script.write_text("#!/usr/bin/env sh\n")
        wrapper = tmp_path / "bin" / "testpilot"
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text(f'#!/usr/bin/env sh\nexec "{console_script}" "$@"\n')

        mock_console = MagicMock()
        with patch("testpilot.cli._get_managed_src", return_value=managed_src):
            with patch("testpilot.cli._get_managed_venv", return_value=managed_venv):
                with patch("testpilot.cli._get_wrapper_path", return_value=wrapper):
                    with patch("testpilot.cli._get_skills_root", return_value=tmp_path / "skills"):
                        with patch("testpilot.cli.console", mock_console):
                            _handle_verify_install()  # must not raise

        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "0.2.0" in output

    def test_missing_skill_fails_even_when_version_ok(self, tmp_path: Path) -> None:
        """Missing skill fails even when all version mirrors are aligned."""
        managed_src = tmp_path / "managed_src"
        managed_src.mkdir()

        (managed_src / "VERSION").write_text("0.2.0\n")
        (managed_src / "pyproject.toml").write_text(
            '[project]\nname = "testpilot"\nversion = "0.2.0"\n'
        )
        init_dir = managed_src / "src" / "testpilot"
        init_dir.mkdir(parents=True)
        (init_dir / "__init__.py").write_text('__version__ = "0.2.0"\n')

        skills_root = tmp_path / "skills"
        expected_skill_path = skills_root / "testpilot-normal-test"
        mock_console = MagicMock()
        # No skill directory created intentionally.
        with patch("testpilot.cli._get_managed_src", return_value=managed_src):
            with patch("testpilot.cli._get_skills_root", return_value=skills_root):
                with patch("testpilot.cli.console", mock_console):
                    with pytest.raises(SystemExit) as exc_info:
                        _handle_verify_install()
        assert exc_info.value.code != 0
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert str(expected_skill_path) in output


# ---------------------------------------------------------------------------
# Managed checkout reporting
# ---------------------------------------------------------------------------


class TestManagedCheckoutReport:
    """_handle_verify_install reports managed checkout status without failing."""

    def test_missing_checkout_does_not_fail(self, tmp_path: Path) -> None:
        """Missing managed checkout is informational, not a hard failure."""
        skill_dir = tmp_path / "skills" / "testpilot-normal-test"
        skill_dir.mkdir(parents=True)

        nonexistent_src = tmp_path / "nonexistent" / "managed" / "src"
        mock_console = MagicMock()
        with patch("testpilot.cli._get_managed_src", return_value=nonexistent_src):
            with patch(
                "testpilot.cli._get_skills_root", return_value=tmp_path / "skills"
            ):
                with patch("testpilot.cli.console", mock_console):
                    _handle_verify_install()  # must not raise

        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        # Some mention of checkout / managed path expected in output.
        assert (
            "checkout" in output.lower()
            or "managed" in output.lower()
            or str(nonexistent_src).split("/")[-2] in output
        )

    def test_healthy_managed_checkout_prints_git_info(self, tmp_path: Path) -> None:
        """When managed checkout exists, verify-install prints git remote/ref/SHA."""
        managed_src = tmp_path / "managed_src"
        managed_src.mkdir()

        (managed_src / "VERSION").write_text("0.2.0\n")
        (managed_src / "pyproject.toml").write_text(
            '[project]\nname = "testpilot"\nversion = "0.2.0"\n'
        )
        init_dir = managed_src / "src" / "testpilot"
        init_dir.mkdir(parents=True)
        (init_dir / "__init__.py").write_text('__version__ = "0.2.0"\n')

        skill_dir = tmp_path / "skills" / "testpilot-normal-test"
        skill_dir.mkdir(parents=True)
        managed_venv = tmp_path / ".venv"
        (managed_venv / "bin").mkdir(parents=True)
        console_script = managed_venv / "bin" / "testpilot"
        console_script.write_text("#!/usr/bin/env sh\n")
        wrapper = tmp_path / "bin" / "testpilot"
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text(f'#!/usr/bin/env sh\nexec "{console_script}" "$@"\n')

        def _fake_git(cmd, **kwargs):
            class _R:
                returncode = 0
                stdout = "abc1234\n"

            if "remote" in cmd:
                _R.stdout = "https://github.com/paulc-arc/testpilot.git\n"
            elif "symbolic-ref" in cmd:
                _R.stdout = "main\n"
            return _R()

        mock_console = MagicMock()
        with patch("testpilot.cli._get_managed_src", return_value=managed_src):
            with patch("testpilot.cli._get_managed_venv", return_value=managed_venv):
                with patch("testpilot.cli._get_wrapper_path", return_value=wrapper):
                    with patch(
                        "testpilot.cli._get_skills_root", return_value=tmp_path / "skills"
                    ):
                        with patch("testpilot.cli._git_run", side_effect=_fake_git):
                            with patch("testpilot.cli.console", mock_console):
                                _handle_verify_install()

        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "abc1234" in output or "paulc-arc" in output or "main" in output


class TestManagedInstallHealthFailures:
    """Broken managed-install wrapper and console script are hard failures."""

    def test_missing_wrapper_fails_when_managed_checkout_exists(self, tmp_path: Path) -> None:
        """Managed checkout without wrapper cannot be considered healthy."""
        from testpilot.cli import _check_wrapper

        managed_src = tmp_path / "managed_src"
        managed_src.mkdir()
        managed_venv = tmp_path / ".venv"
        wrapper = tmp_path / "bin" / "testpilot"

        ok, msg = _check_wrapper(wrapper, managed_venv, managed_src)

        assert not ok
        assert str(wrapper) in msg

    def test_missing_console_script_fails_when_managed_checkout_exists(
        self, tmp_path: Path
    ) -> None:
        """Managed checkout without venv console script cannot be considered healthy."""
        from testpilot.cli import _check_console_script

        managed_src = tmp_path / "managed_src"
        managed_src.mkdir()
        managed_venv = tmp_path / ".venv"

        ok, msg = _check_console_script(managed_venv, managed_src)

        assert not ok
        assert "console_script" in msg


# ---------------------------------------------------------------------------
# serialwrap venv-first check (I-3)
# ---------------------------------------------------------------------------


class TestSerialwrapVenvCheck:
    """_check_serialwrap_available must prefer managed-venv serialwrap over PATH."""

    def test_serialwrap_found_in_managed_venv(self, tmp_path: Path) -> None:
        """serialwrap present in managed venv is reported OK even if not in PATH."""
        from unittest.mock import patch

        from testpilot.cli import _check_serialwrap_available

        managed_venv = tmp_path / ".venv"
        (managed_venv / "bin").mkdir(parents=True)
        sw = managed_venv / "bin" / "serialwrap"
        sw.write_text("#!/usr/bin/env sh\n")
        sw.chmod(0o755)

        with patch("testpilot.cli._get_managed_venv", return_value=managed_venv):
            # Remove serialwrap from PATH to prove venv-first logic.
            with patch("testpilot.cli.shutil.which", return_value=None):
                ok, msg = _check_serialwrap_available()

        assert ok, f"expected OK but got: {msg}"
        assert "serialwrap" in msg.lower(), f"expected 'serialwrap' in message: {msg}"
        assert str(managed_venv) in msg, (
            f"expected managed venv path {managed_venv} in message: {msg}"
        )
