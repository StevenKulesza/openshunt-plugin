#!/bin/bash
# Provider-neutral one-shot delegation; requests never travel through argv.
SHUNT_TRANSPORT_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/transport.py"
SHUNT_TMPFILES=()
shunt_tmpfile() {
  local f
  f=$(mktemp) || return 1
  SHUNT_TMPFILES+=("$f")
  trap 'rm -f "${SHUNT_TMPFILES[@]}"' EXIT
  printf -v "$1" '%s' "$f"
}
shunt_preflight() {
  command -v python3 >/dev/null 2>&1 || { echo 'Error: python3 is required' >&2; return 1; }
}
shunt_invoke() {
  python3 "$SHUNT_TRANSPORT_PY" "$1" "$2"
}
