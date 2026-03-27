#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# TestPilot Install Script
#   Installs testpilot + serialwrap + all required dependencies.
#
# Usage:
#   curl -sSL <url>/install.sh | bash
#   # or
#   bash scripts/install.sh
#
# Requirements:
#   - Python 3.11+
#   - pip or uv
#   - git
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
CYAN="\033[36m"
RESET="\033[0m"

info()  { echo -e "${CYAN}[INFO]${RESET}  $*"; }
ok()    { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
fail()  { echo -e "${RED}[FAIL]${RESET}  $*"; exit 1; }

# ── 1. Check prerequisites ───────────────────────────────────────────
info "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || fail "python3 not found. Please install Python 3.11+."
command -v git     >/dev/null 2>&1 || fail "git not found. Please install git."

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VER" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VER" | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    fail "Python 3.11+ required, found $PYTHON_VER"
fi
ok "Python $PYTHON_VER"

# Prefer uv over pip
USE_UV=false
if command -v uv >/dev/null 2>&1; then
    USE_UV=true
    ok "uv found (preferred)"
else
    warn "uv not found, using pip"
    command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1 || fail "pip not found"
fi

# ── 2. Determine project root ────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../pyproject.toml" ]; then
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -f "./pyproject.toml" ]; then
    PROJECT_ROOT="$(pwd)"
else
    fail "Cannot find pyproject.toml. Run from the testpilot repo root or scripts/ dir."
fi
info "Project root: $PROJECT_ROOT"

# ── 3. Create virtualenv ─────────────────────────────────────────────
VENV_DIR="$PROJECT_ROOT/.venv"
if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtualenv at $VENV_DIR ..."
    if $USE_UV; then
        uv venv "$VENV_DIR"
    else
        python3 -m venv "$VENV_DIR"
    fi
    ok "Virtualenv created"
else
    ok "Virtualenv exists"
fi

# Activate
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
ok "Virtualenv activated"

# ── 4. Install testpilot (editable + dev deps) ───────────────────────
info "Installing testpilot [dev] ..."
if $USE_UV; then
    uv pip install -e "$PROJECT_ROOT[dev]" --quiet
else
    pip install -e "$PROJECT_ROOT[dev]" --quiet
fi
ok "testpilot installed"

# ── 5. Install serialwrap ────────────────────────────────────────────
info "Checking serialwrap..."
if command -v serialwrap >/dev/null 2>&1; then
    SW_VER=$(serialwrap --version 2>&1 || echo "unknown")
    ok "serialwrap already installed ($SW_VER)"
else
    info "Installing serialwrap..."
    if $USE_UV; then
        uv pip install serialwrap --quiet 2>/dev/null || warn "serialwrap not available via pip — install manually"
    else
        pip install serialwrap --quiet 2>/dev/null || warn "serialwrap not available via pip — install manually"
    fi
    if command -v serialwrap >/dev/null 2>&1; then
        ok "serialwrap installed"
    else
        warn "serialwrap not found after install. You may need to install it manually."
        warn "  See: https://github.com/nicebots-xyz/serialwrap"
    fi
fi

# ── 6. Copy example config ───────────────────────────────────────────
TESTBED_CONF="$PROJECT_ROOT/configs/testbed.yaml"
TESTBED_EXAMPLE="$PROJECT_ROOT/configs/testbed.yaml.example"
if [ ! -f "$TESTBED_CONF" ] && [ -f "$TESTBED_EXAMPLE" ]; then
    cp "$TESTBED_EXAMPLE" "$TESTBED_CONF"
    ok "Copied testbed.yaml.example → testbed.yaml (edit for your lab)"
else
    ok "testbed.yaml already exists"
fi

# ── 7. Verify installation ───────────────────────────────────────────
info "Verifying installation..."
python3 -m testpilot.cli --version || fail "testpilot CLI not working"
ok "testpilot CLI verified"

python3 -m testpilot.cli list-plugins || warn "Plugin loading issue (may need testbed config)"

# ── 8. Summary ────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}════════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}  TestPilot installation complete!${RESET}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Quick start:${RESET}"
echo -e "    source $VENV_DIR/bin/activate"
echo -e "    testpilot --version"
echo -e "    testpilot list-plugins"
echo -e "    testpilot list-cases wifi_llapi"
echo ""
echo -e "  ${BOLD}Run with Azure OpenAI:${RESET}"
echo -e "    testpilot --azure run wifi_llapi"
echo ""
echo -e "  ${BOLD}Run with GitHub OAuth (default):${RESET}"
echo -e "    testpilot run wifi_llapi"
echo ""
echo -e "  ${BOLD}Edit testbed config:${RESET}"
echo -e "    vi $TESTBED_CONF"
echo ""
