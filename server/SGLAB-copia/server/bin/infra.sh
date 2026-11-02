#!/usr/bin/env bash
# Mantener la ruta anterior; la administración ahora está en infra/infra.sh.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1
exec bash "$SCRIPT_DIR/../../infra/infra.sh" "$@"
