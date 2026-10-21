#!/usr/bin/env bash
#
# Duplicate File Scanner - Linux installer
#
# What it does:
#   1. Finds Python 3.10+ that also has tkinter and venv support
#      (installs them with your package manager if they are missing)
#   2. Creates a virtual environment in ./.venv
#   3. Installs the Python dependencies into it
#
# Why the system package manager? tkinter (the GUI toolkit) and venv are NOT
# installable with pip on most Linux distros - they come from packages like
# "python3-tk" - so this script installs those parts for you.
#
# Usage:
#   ./install.sh          install what is needed to RUN the app
#   ./install.sh --dev    also install the test tools (pytest)
#   ./install.sh --help   show this text

set -euo pipefail

# Always work from the folder this script lives in, wherever it is called from.
cd "$(dirname "${BASH_SOURCE[0]}")"

MIN_MAJOR=3
MIN_MINOR=10
VENV_DIR=".venv"
INSTALL_DEV=0

# ---------------------------------------------------------------------------
# Pretty output (colours only when printing to a real terminal)
# ---------------------------------------------------------------------------
if [[ -t 1 ]]; then
    BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
    BOLD=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

step() { echo; echo "${BOLD}==> $*${RESET}"; }
ok()   { echo "  ${GREEN}[ok]${RESET} $*"; }
warn() { echo "  ${YELLOW}[!!]${RESET} $*"; }
die()  { echo; echo "${RED}ERROR:${RESET} $*" >&2; exit 1; }

usage() {
    cat <<'EOF'
Usage:
  ./install.sh          install what is needed to run the app
  ./install.sh --dev    also install the test tools (pytest)
  ./install.sh --help   show this text
EOF
}

for arg in "$@"; do
    case "$arg" in
        --dev)     INSTALL_DEV=1 ;;
        -h|--help) usage; exit 0 ;;
        *)         usage; die "Unknown option: $arg" ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Print the path of the first Python that is new enough AND has tkinter AND
# can create virtual environments. Returns non-zero if there isn't one.
find_python() {
    local candidate
    for candidate in python3 python3.14 python3.13 python3.12 python3.11 python3.10 python; do
        command -v "$candidate" >/dev/null 2>&1 || continue
        if "$candidate" - >/dev/null 2>&1 <<EOF
import sys
if sys.version_info < ($MIN_MAJOR, $MIN_MINOR):
    sys.exit(1)
import tkinter          # GUI toolkit (system package on Linux)
import ensurepip, venv  # needed to create a virtual environment
EOF
        then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

# Run a command as root: directly if we already are, otherwise via sudo.
run_privileged() {
    if [[ $EUID -eq 0 ]]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        die "Root rights are needed to install system packages, but 'sudo' was not found. Re-run this script as root, or install the packages yourself: $*"
    fi
}

# Ask a yes/no question (default: yes). Skipped when not run interactively.
confirm() {
    [[ -t 0 ]] || return 0
    local reply
    read -r -p "  $1 [Y/n] " reply
    [[ -z "$reply" || "$reply" =~ ^[Yy] ]]
}

install_system_packages() {
    if command -v apt-get >/dev/null 2>&1; then
        warn "Debian/Ubuntu family detected: installing python3, python3-venv, python3-pip, python3-tk"
        confirm "Install them with apt now?" || die "Cancelled."
        run_privileged apt-get update
        run_privileged apt-get install -y python3 python3-venv python3-pip python3-tk
    elif command -v dnf >/dev/null 2>&1; then
        warn "Fedora/RHEL family detected: installing python3, python3-pip, python3-tkinter"
        confirm "Install them with dnf now?" || die "Cancelled."
        run_privileged dnf install -y python3 python3-pip python3-tkinter
    elif command -v pacman >/dev/null 2>&1; then
        warn "Arch family detected: installing python, python-pip, tk"
        confirm "Install them with pacman now?" || die "Cancelled."
        run_privileged pacman -S --needed --noconfirm python python-pip tk
    elif command -v zypper >/dev/null 2>&1; then
        warn "openSUSE detected: installing python3, python3-pip, python3-tk"
        confirm "Install them with zypper now?" || die "Cancelled."
        run_privileged zypper --non-interactive install python3 python3-pip python3-tk
    else
        die "Could not detect a supported package manager (apt, dnf, pacman, zypper). Please install Python ${MIN_MAJOR}.${MIN_MINOR}+ with tkinter and venv support yourself, then run this script again."
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

[[ -f requirements.txt ]] || die "requirements.txt not found. Run this script from the project folder."

if [[ $EUID -eq 0 ]]; then
    warn "Running as root: the .venv folder will be owned by root. Prefer running without sudo (the script asks for it only when needed)."
fi

step "Looking for Python ${MIN_MAJOR}.${MIN_MINOR}+ with tkinter and venv support"
PYTHON="$(find_python || true)"

if [[ -z "$PYTHON" ]]; then
    warn "No suitable Python found (needs ${MIN_MAJOR}.${MIN_MINOR}+, tkinter and venv)."
    install_system_packages
    PYTHON="$(find_python || true)"
    [[ -n "$PYTHON" ]] || die "Still no suitable Python after installing packages. Your distro's default Python may be older than ${MIN_MAJOR}.${MIN_MINOR}. Install a newer one (for example with pyenv, or your distro's backports) and run this script again."
fi
ok "Using $PYTHON ($("$PYTHON" --version 2>&1))"

step "Creating virtual environment in ${VENV_DIR}/"
if [[ -x "${VENV_DIR}/bin/python" ]]; then
    ok "Already exists - reusing it"
else
    "$PYTHON" -m venv "$VENV_DIR"
    ok "Created"
fi
VENV_PY="${VENV_DIR}/bin/python"

step "Installing Python dependencies"
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt
ok "Installed requirements.txt"

if (( INSTALL_DEV )); then
    [[ -f requirements-dev.txt ]] || die "requirements-dev.txt not found."
    "$VENV_PY" -m pip install -r requirements-dev.txt
    ok "Installed requirements-dev.txt (test tools)"
fi

step "Checking the installation"
"$VENV_PY" -c "import tkinter, customtkinter, send2trash" \
    || die "Something did not install correctly. Scroll up for the error."
ok "tkinter, customtkinter and send2trash all import fine"

echo
echo "${GREEN}${BOLD}All done!${RESET}"
echo "  Start the app:   ./run.sh"
if (( INSTALL_DEV )); then
    echo "  Run the tests:   ${VENV_DIR}/bin/python -m pytest -v"
fi
echo