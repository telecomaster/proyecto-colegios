#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Deteniendo Proyecto Colegios..."
docker compose down
echo "Listo."
