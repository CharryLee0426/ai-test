#!/usr/bin/env bash
# run-all-cases.sh — For each cases/*.md, invoke Codex non-interactively with a computer-control prompt.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run-all-cases.sh [OPTIONS] [-- EXTRA_CODEX_ARGS...]

  --repo-root PATH   Project root (default: parent of this script's directory)
  --dry-run          Print what would run, do not invoke codex
  -h, --help         Show this help

Environment:
  CODEX_BIN          codex executable (default: codex)
  CODEX_EXEC_PREFIX  Extra args before the prompt (default: see below)
                       Default matches interactive /permissions → full access for `codex exec`:
                       --dangerously-bypass-approvals-and-sandbox
                       Safer alternative: CODEX_EXEC_PREFIX='--full-auto'

Any arguments after `--` are appended to the codex exec invocation (after CODEX_EXEC_PREFIX).

Example:
  ./scripts/run-all-cases.sh
  ./scripts/run-all-cases.sh --dry-run
  CODEX_EXEC_PREFIX='--full-auto' ./scripts/run-all-cases.sh -- -m gpt-5.1-codex-max
EOF
}

REPO_ROOT=""
DRY_RUN=0
EXTRA_AFTER_DD=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="${2:?}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      EXTRA_AFTER_DD=("$@")
      break
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

CODEX_BIN="${CODEX_BIN:-codex}"
# Default: same idea as interactive /permissions → full access (no sandbox, no approval prompts).
CODEX_EXEC_PREFIX="${CODEX_EXEC_PREFIX:---dangerously-bypass-approvals-and-sandbox}"

CASES_DIR="$REPO_ROOT/cases"
if [[ ! -d "$CASES_DIR" ]]; then
  echo "Cases directory not found: $CASES_DIR" >&2
  exit 1
fi

if ! command -v "$CODEX_BIN" >/dev/null 2>&1; then
  echo "codex not found (CODEX_BIN=$CODEX_BIN). Install the Codex CLI or set CODEX_BIN." >&2
  exit 1
fi

shopt -s nullglob
case_files=("$CASES_DIR"/*.md)
shopt -u nullglob

if [[ "${#case_files[@]}" -eq 0 || ! -f "${case_files[0]:-}" ]]; then
  echo "No .md files under $CASES_DIR" >&2
  exit 1
fi

# Deterministic order (bash 3.2–compatible; no mapfile).
sorted_case_files=()
while IFS= read -r line; do
  [[ -n "$line" ]] && sorted_case_files+=("$line")
done < <(printf '%s\n' "${case_files[@]}" | sort)

failed=0
for case_path in "${sorted_case_files[@]}"; do
  [[ -f "$case_path" ]] || continue
  name="$(basename "$case_path")"
  prompt="Use computer-control to execute the instruction in ${name} in the cases folder."

  # shellcheck disable=SC2206
  prefix_args=($CODEX_EXEC_PREFIX)

  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run]'
    printf ' %q' "$CODEX_BIN" exec "${prefix_args[@]}" -C "$REPO_ROOT" "$prompt" \
      ${EXTRA_AFTER_DD[@]+"${EXTRA_AFTER_DD[@]}"}
    echo
    continue
  fi

  echo "=== Case: $name ===" >&2
  if "$CODEX_BIN" exec "${prefix_args[@]}" -C "$REPO_ROOT" "$prompt" \
    ${EXTRA_AFTER_DD[@]+"${EXTRA_AFTER_DD[@]}"}; then
    echo "=== OK: $name ===" >&2
  else
    echo "=== FAILED: $name (exit $?) ===" >&2
    failed=1
  fi
done

exit "$failed"
