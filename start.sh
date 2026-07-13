#!/usr/bin/env bash
# Arranca el sistema en Linux / Raspberry Pi.
# Requiere: Docker Engine + plugin compose, y Ollama corriendo como servicio
# del sistema (systemctl status ollama).
set -euo pipefail
cd "$(dirname "$0")"

echo "========================================"
echo "  Proyecto Colegios - Asistente Virtual"
echo "========================================"
echo

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
MODEL_NAME="${MODEL_NAME:-llama3.2:3b-instruct-q4_K_M}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "ERROR: no se encontro el comando 'ollama'. Instalar con:"
  echo "  curl -fsSL https://ollama.com/install.sh | sh"
  exit 1
fi

if ! systemctl is-active --quiet ollama 2>/dev/null; then
  echo "AVISO: el servicio 'ollama' no aparece activo via systemd."
  echo "       Si lo estas corriendo manualmente (ollama serve), ignora este aviso."
fi

echo "[1/3] Verificando/descargando el modelo ${MODEL_NAME}..."
ollama pull "${MODEL_NAME}"

echo
echo "[2/3] Construyendo y levantando los contenedores Docker..."
docker compose up -d --build

echo
echo "[3/3] Esperando a que el orchestrator responda..."
for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo
echo "========================================"
echo "  LISTO"
echo "========================================"
echo
echo "  Interfaz:      http://localhost:3000"
echo "  (desde otro dispositivo en la red: http://$(hostname -I 2>/dev/null | awk '{print $1}'):3000)"
echo "  API docs:      http://localhost:8000/docs"
echo "  Health check:  http://localhost:8000/health"
echo
