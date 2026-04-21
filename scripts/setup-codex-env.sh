#!/usr/bin/env bash
# setup-codex-env.sh — Install Codex CLI, create project folders, sync skills to ~/.codex/skills/
# Compatible with bash and zsh when executed (not when sourced).
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: setup-codex-env.sh [OPTIONS]

  --repo-root PATH   Project root (default: parent of this script's directory)
  --skip-codex       Do not install / upgrade the Codex CLI
  --codex-method auto|npm|brew
                     How to install Codex (default: auto)
  --link-skills      Symlink skills into ~/.codex/skills/ instead of copying
  -h, --help         Show this help

Environment:
  NPM_BIN   npm executable (default: npm)
  BREW_BIN  brew executable (default: brew)
EOF
}

REPO_ROOT=""
SKIP_CODEX=0
CODEX_METHOD="auto"
LINK_SKILLS=0
NPM_BIN="${NPM_BIN:-npm}"
BREW_BIN="${BREW_BIN:-brew}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="${2:?}"
      shift 2
      ;;
    --skip-codex)
      SKIP_CODEX=1
      shift
      ;;
    --codex-method)
      CODEX_METHOD="${2:?}"
      shift 2
      ;;
    --link-skills)
      LINK_SKILLS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

have_cmd() { command -v "$1" >/dev/null 2>&1; }

install_codex_npm() {
  if ! have_cmd "$NPM_BIN"; then
    return 1
  fi
  echo "Installing Codex CLI via npm: $NPM_BIN install -g @openai/codex"
  "$NPM_BIN" install -g @openai/codex
}

install_codex_brew() {
  if ! have_cmd "$BREW_BIN"; then
    return 1
  fi
  echo "Installing Codex CLI via Homebrew: $BREW_BIN install codex"
  "$BREW_BIN" install codex
}

install_codex() {
  case "$CODEX_METHOD" in
    npm)
      install_codex_npm
      ;;
    brew)
      install_codex_brew
      ;;
    auto)
      if have_cmd "$NPM_BIN"; then
        install_codex_npm || install_codex_brew
      elif have_cmd "$BREW_BIN"; then
        install_codex_brew
      else
        echo "Neither npm nor brew found. Install Node.js (npm) or Homebrew, then re-run." >&2
        echo "Manual install: npm install -g @openai/codex   OR   brew install codex" >&2
        exit 1
      fi
      ;;
    *)
      echo "Invalid --codex-method: $CODEX_METHOD (use auto, npm, or brew)" >&2
      exit 2
      ;;
  esac
}

if [[ "$SKIP_CODEX" -eq 0 ]]; then
  install_codex
else
  echo "Skipping Codex CLI install (--skip-codex)."
fi

if ! have_cmd codex; then
  echo "Warning: 'codex' not found on PATH after install step. Open a new terminal or fix your PATH." >&2
else
  echo "Codex CLI: $(command -v codex)"
  codex --version 2>/dev/null || true
fi

echo "Creating folders under: $REPO_ROOT"
mkdir -p "$REPO_ROOT/cases" "$REPO_ROOT/reports" "$REPO_ROOT/tests"

CODEX_SKILLS_HOME="${CODEX_SKILLS_HOME:-$HOME/.codex/skills}"
echo "Syncing skills to: $CODEX_SKILLS_HOME"
mkdir -p "$CODEX_SKILLS_HOME"

SKILLS_SRC="$REPO_ROOT/skills"
if [[ ! -d "$SKILLS_SRC" ]]; then
  echo "No skills directory at $SKILLS_SRC — nothing to install." >&2
else
  shopt -s nullglob
  found=0
  for skill_dir in "$SKILLS_SRC"/*/; do
    [[ -d "$skill_dir" ]] || continue
    found=1
    name="$(basename "${skill_dir%/}")"
    dest="$CODEX_SKILLS_HOME/$name"
    rm -rf "$dest"
    if [[ "$LINK_SKILLS" -eq 1 ]]; then
      echo "  link: $name -> $dest"
      ln -s "$skill_dir" "$dest"
    else
      echo "  copy: $name"
      cp -R "$skill_dir" "$dest"
    fi
  done
  if [[ "$found" -eq 0 ]]; then
    echo "No subdirectories under $SKILLS_SRC — nothing to install." >&2
  fi
fi

echo "Done."
echo "  cases:   $REPO_ROOT/cases"
echo "  reports: $REPO_ROOT/reports"
echo "  tests:   $REPO_ROOT/tests"
echo "  skills:  $CODEX_SKILLS_HOME"
